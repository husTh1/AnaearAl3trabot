"""
التحقق من اشتراك المستخدم (مالك القناة) بالقناة الرسمية الإجبارية.
هذا التحقق يتم بشكل حي (real-time) في كل مرة:
- عند إضافة البوت لقناة جديدة
- قبل كل عملية نشر مجدولة لكل قناة (لضمان أن المالك لا يزال مشتركًا)

⚠️ متطلب أساسي: يجب أن يكون البوت أدمن في القناة الرسمية أيضًا
(وليس فقط في قنوات النشر)، وإلا ستفشل كل عمليات التحقق.
"""
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden

from bot.config import OFFICIAL_CHANNEL_USERNAME, logger

# حالات العضوية التي تُعتبر "مشتركًا فعليًا" في تيليجرام
SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


async def is_user_subscribed(bot: Bot, user_id: int) -> bool:
    """
    يتحقق مما إذا كان المستخدم عضوًا في القناة الرسمية.
    يرجع False أيضًا في حال حدوث أي خطأ (فشل آمن - Fail Safe)
    بدل السماح بالمرور عند الشك.
    """
    channel = f"@{OFFICIAL_CHANNEL_USERNAME}"
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in SUBSCRIBED_STATUSES
    except Forbidden:
        logger.error(
            "البوت ليس أدمن في القناة الرسمية %s - لا يمكن التحقق من الاشتراك. "
            "يرجى إضافة البوت كأدمن في هذه القناة.",
            channel,
        )
        return False
    except BadRequest as e:
        logger.warning("تعذر التحقق من اشتراك المستخدم %s: %s", user_id, e)
        return False
    except TelegramError as e:
        logger.warning("خطأ تيليجرام غير متوقع أثناء التحقق من الاشتراك: %s", e)
        return False


def official_channel_link() -> str:
    return f"https://t.me/{OFFICIAL_CHANNEL_USERNAME}"


async def verify_bot_is_admin_in_official_channel(bot: Bot) -> bool:
    """
    فحص إقلاع (Startup Check): يتأكد أن البوت نفسه أدمن في القناة الرسمية.
    كل آلية الاشتراك الإجباري تعتمد على هذا الشرط - إن لم يتحقق،
    ستفشل كل عمليات is_user_subscribed بصمت وتُعطَّل كل القنوات خطأً.
    """
    channel = f"@{OFFICIAL_CHANNEL_USERNAME}"
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=channel, user_id=me.id)
        if member.status not in ("administrator", "creator"):
            logger.critical(
                "⚠️ البوت ليس أدمن في القناة الرسمية %s (الحالة الحالية: %s). "
                "لن تعمل آلية الاشتراك الإجباري إطلاقًا حتى تضيف البوت كأدمن هناك.",
                channel, member.status,
            )
            return False
        logger.info("تم التحقق: البوت أدمن في القناة الرسمية %s ✅", channel)
        return True
    except TelegramError as e:
        logger.critical(
            "⚠️ تعذر التحقق من عضوية البوت في القناة الرسمية %s: %s. "
            "تأكد أن اسم القناة صحيح وأن البوت أضيف إليها كأدمن.",
            channel, e,
        )
        return False
