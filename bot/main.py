"""
نقطة الدخول الرئيسية للبوت.
تشغيل: python -m bot.main
"""
from datetime import time as dtime
from zoneinfo import ZoneInfo

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ChatMemberHandler,
    ContextTypes,
)

from bot.config import BOT_TOKEN, CHANNELS_FILE, CONTENT_STATE_FILE, ADMIN_ID, logger
from bot.storage import ChannelStore, ContentStateStore
from bot.content_manager import ContentManager
from bot.scheduler import schedule_today_jobs
from bot.subscription import verify_bot_is_admin_in_official_channel
from bot import handlers


async def _post_init(application: Application) -> None:
    """يُنفَّذ مرة واحدة فور بدء تشغيل البوت - يهيّئ جدول اليوم الحالي فورًا."""
    logger.info("تشغيل البوت - جاري جلب أوقات الصلاة وجدولة نشر اليوم...")

    is_ready = await verify_bot_is_admin_in_official_channel(application.bot)
    if not is_ready:
        warning = (
            "🚨 تحذير هام: البوت ليس أدمن في القناة الرسمية، أو اسمها خاطئ في الإعدادات.\n"
            "آلية الاشتراك الإجباري لن تعمل، وسيتم رفض تفعيل كل القنوات حتى تصلح هذا.\n"
            "أضف البوت كأدمن في القناة الرسمية ثم أعد تشغيله."
        )
        try:
            await application.bot.send_message(chat_id=ADMIN_ID, text=warning)
        except Exception:
            pass

    await schedule_today_jobs(application.job_queue)


async def _daily_refresh_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """مهمة يومية تعمل بعد منتصف الليل بقليل لجدولة أوقات اليوم الجديد."""
    await schedule_today_jobs(context.job_queue)


def build_application() -> Application:
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # تهيئة المخازن ووحدة المحتوى ومشاركتها بين كل المعالجات عبر bot_data
    application.bot_data["channel_store"] = ChannelStore(CHANNELS_FILE)
    application.bot_data["content_manager"] = ContentManager(ContentStateStore(CONTENT_STATE_FILE))

    # أوامر المستخدمين
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("mychannels", handlers.mychannels_command))
    application.add_handler(CommandHandler("reactivate", handlers.reactivate_command))

    # أوامر إدارية
    application.add_handler(CommandHandler("test", handlers.test_command))
    application.add_handler(CommandHandler("status", handlers.status_command))
    application.add_handler(CommandHandler("postnow", handlers.post_now_command))

    # حدث تغيّر صلاحية البوت في أي قناة (إضافة/إزالة كأدمن)
    application.add_handler(ChatMemberHandler(handlers.my_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    # مهمة يومية لإعادة جلب أوقات الصلاة وجدولة نشر اليوم الجديد (00:05 بتوقيت بغداد تقريبيًا)
    application.job_queue.run_daily(
        _daily_refresh_job,
        time=dtime(hour=0, minute=5, tzinfo=ZoneInfo("Asia/Baghdad")),
        name="daily_schedule_refresh",
    )

    return application


def main() -> None:
    application = build_application()
    logger.info("البوت يعمل الآن...")
    application.run_polling(allowed_updates=["message", "my_chat_member"])


if __name__ == "__main__":
    main()
