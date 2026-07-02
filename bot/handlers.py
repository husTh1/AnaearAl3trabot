"""
معالجات الأوامر والأحداث:
- /start: ترحيب وشرح آلية الاشتراك الإجباري
- my_chat_member: يُستدعى تلقائيًا عندما يُضاف البوت كأدمن لقناة (أو يُزال منها)
- /mychannels: عرض قنوات المستخدم المسجَّلة
- /reactivate: إعادة تفعيل قناة بعد الاشتراك من جديد
- /test و /status: أوامر إدارية للمالك فقط
"""
from telegram import Update
from telegram.constants import ChatType, ChatMemberStatus
from telegram.ext import ContextTypes

from bot.config import ADMIN_ID, logger
from bot.subscription import is_user_subscribed, official_channel_link
from bot.scheduler import post_to_all_channels
from bot.message_formatter import format_bundle, format_preview_header

ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🕌 السلام عليكم ورحمة الله وبركاته\n\n"
        "أنا بوت لنشر الآيات القرآنية والأحاديث الشريفة عن أهل البيت عليهم السلام "
        "والأدعية والأذكار تلقائيًا في قناتك، بالتزامن مع أوقات الصلاة الخمسة.\n\n"
        "📌 لتفعيل البوت في قناتك:\n"
        f"1️⃣ اشترك أولًا في قناتنا الرسمية: {official_channel_link()}\n"
        "2️⃣ أضف هذا البوت كأدمن في قناتك (مع صلاحية إرسال الرسائل)\n"
        "3️⃣ سيبدأ النشر تلقائيًا خلال أقرب وقت صلاة\n\n"
        "⚠️ ملاحظة: الاشتراك بالقناة الرسمية إجباري ومستمر - "
        "إن غادرتها لاحقًا سيتوقف النشر في قناتك تلقائيًا حتى تعود.\n\n"
        "الأوامر المتاحة:\n"
        "/mychannels - عرض قنواتي المسجَّلة\n"
        "/reactivate - إعادة تفعيل قناتي بعد الاشتراك من جديد"
    )
    await update.message.reply_text(text)


async def my_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يُستدعى تلقائيًا كلما تغيرت صلاحية البوت في أي قناة أو مجموعة."""
    chat_member_update = update.my_chat_member
    chat = chat_member_update.chat
    new_status = chat_member_update.new_chat_member.status
    old_status = chat_member_update.old_chat_member.status
    actor = chat_member_update.from_user  # الشخص الذي قام بالإجراء

    channel_store = context.bot_data["channel_store"]

    if chat.type != ChatType.CHANNEL:
        return  # نتعامل فقط مع القنوات، وليس المجموعات أو الخاص

    became_admin = new_status in ADMIN_STATUSES and old_status not in ADMIN_STATUSES
    lost_admin = new_status not in ADMIN_STATUSES and old_status in ADMIN_STATUSES

    if became_admin:
        subscribed = await is_user_subscribed(context.bot, actor.id)
        if subscribed:
            channel_store.register(chat.id, actor.id, chat.title or str(chat.id))
            logger.info("تم تسجيل القناة '%s' (%s) من قبل المستخدم %s", chat.title, chat.id, actor.id)
            try:
                await context.bot.send_message(
                    chat_id=actor.id,
                    text=(
                        f"✅ تم تفعيل النشر التلقائي في قناتك «{chat.title}» بنجاح!\n"
                        "سيبدأ نشر المحتوى مع أقرب وقت صلاة إن شاء الله."
                    ),
                )
            except Exception:
                pass  # المستخدم قد لا يكون بدأ محادثة خاصة مع البوت بعد
        else:
            logger.info(
                "تمت إضافة البوت للقناة '%s' لكن المستخدم %s غير مشترك بالقناة الرسمية - لن يتم التفعيل",
                chat.title, actor.id,
            )
            try:
                await context.bot.send_message(
                    chat_id=actor.id,
                    text=(
                        f"⚠️ لتفعيل النشر في قناتك «{chat.title}»، يجب أولًا الاشتراك في قناتنا الرسمية:\n"
                        f"{official_channel_link()}\n\n"
                        "بعد الاشتراك، أرسل لي الأمر /reactivate هنا في الخاص."
                    ),
                )
            except Exception:
                pass

    elif lost_admin:
        channel_store.deactivate(chat.id, reason="bot_removed_or_demoted")
        logger.info("تم تعطيل القناة '%s' (%s) لأن البوت لم يعد أدمن فيها", chat.title, chat.id)


async def mychannels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_store = context.bot_data["channel_store"]
    user_id = update.effective_user.id
    channels = channel_store.get_by_owner(user_id)

    if not channels:
        await update.message.reply_text(
            "لا توجد لديك أي قناة مسجَّلة بعد.\n"
            "أضف البوت كأدمن في قناتك بعد الاشتراك بالقناة الرسمية لتفعيل النشر."
        )
        return

    lines = ["📋 قنواتك المسجَّلة:\n"]
    for channel_id, info in channels.items():
        status = "✅ نشطة" if info.get("active") else "⛔ متوقفة"
        lines.append(f"• {info.get('channel_title', channel_id)} - {status}")
    await update.message.reply_text("\n".join(lines))


async def reactivate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_store = context.bot_data["channel_store"]
    user_id = update.effective_user.id

    subscribed = await is_user_subscribed(context.bot, user_id)
    if not subscribed:
        await update.message.reply_text(
            f"❌ ما زلت غير مشترك بالقناة الرسمية:\n{official_channel_link()}\n"
            "اشترك أولًا ثم أعد إرسال /reactivate."
        )
        return

    channels = channel_store.get_by_owner(user_id)
    if not channels:
        await update.message.reply_text("لا توجد لديك قنوات مسجَّلة لإعادة تفعيلها.")
        return

    count = 0
    for channel_id in channels:
        channel_store.reactivate(int(channel_id))
        count += 1

    await update.message.reply_text(f"✅ تم إعادة تفعيل النشر في {count} قناة/قنوات. الحمد لله.")


def _admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            return
        return await func(update, context)
    return wrapper


@_admin_only
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر إداري: يرسل معاينة لشكل الرسالة في الخاص قبل الاعتماد على النشر الفعلي."""
    content_manager = context.bot_data["content_manager"]
    bundle = content_manager.build_daily_bundle()
    text = format_bundle(bundle, prayer_key="Dhuhr")
    await update.message.reply_text(format_preview_header() + text)


@_admin_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    channel_store = context.bot_data["channel_store"]
    all_channels = channel_store.get_all()
    active = [c for c in all_channels.values() if c.get("active")]
    inactive = [c for c in all_channels.values() if not c.get("active")]

    lines = [
        "📊 حالة البوت:",
        f"عدد القنوات المسجَّلة: {len(all_channels)}",
        f"✅ نشطة: {len(active)}",
        f"⛔ متوقفة: {len(inactive)}",
    ]
    await update.message.reply_text("\n".join(lines))


@_admin_only
async def post_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر إداري: ينشر فورًا في كل القنوات النشطة (لأغراض الاختبار الفعلي)."""
    result = await post_to_all_channels(context, prayer_key=None)
    await update.message.reply_text(
        f"تم النشر. ناجح: {result['posted']} | "
        f"متوقف (غير مشترك): {result['skipped_unsubscribed']} | "
        f"فشل: {result['failed']}"
    )
