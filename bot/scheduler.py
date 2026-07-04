"""
جدولة النشر التلقائي عند كل صلاة من الصلوات الخمس.

يعتمد على Aladhan API (مجاني بالكامل، بدون مفتاح API) لحساب الأوقات يوميًا
باستخدام منهج "Shia Ithna-Ashari" (method=0) المناسب للتوجه الشيعي للمشروع.

في حال فشل الاتصال بـ Aladhan لأي سبب، يستخدم البوت جدولًا احتياطيًا ثابتًا
تقريبيًا حتى لا يتوقف النشر بالكامل.
"""
import datetime
from zoneinfo import ZoneInfo

import httpx
from telegram.ext import ContextTypes, JobQueue

from bot.config import PRAYER_LATITUDE, PRAYER_LONGITUDE, ALADHAN_METHOD, logger
from bot.subscription import is_user_subscribed
from bot.message_formatter import format_bundle

ALADHAN_URL = "https://api.aladhan.com/v1/timings"

PRAYER_KEYS = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]

# جدول احتياطي تقريبي (بتوقيت بغداد) يُستخدم فقط إذا فشل الاتصال بـ Aladhan
FALLBACK_TIMES = {
    "Fajr": "04:30",
    "Dhuhr": "12:30",
    "Asr": "16:00",
    "Maghrib": "19:15",
    "Isha": "20:45",
}
FALLBACK_TIMEZONE = "Asia/Baghdad"


async def fetch_prayer_times() -> tuple[dict, str]:
    """
    يجلب أوقات الصلاة الخمسة لليوم الحالي من Aladhan API باستخدام إحداثيات دقيقة
    (بدل اسم مدينة نصي)، مما يزيل خطوة "ترجمة الاسم لإحداثيات" الوسيطة ويجعل
    الحساب الفلكي مباشرًا وأدق.
    يرجع (dict بالأوقات، اسم المنطقة الزمنية).
    """
    today_str = datetime.date.today().strftime("%d-%m-%Y")
    url = f"{ALADHAN_URL}/{today_str}"
    params = {
        "latitude": PRAYER_LATITUDE,
        "longitude": PRAYER_LONGITUDE,
        "method": ALADHAN_METHOD,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        timings = payload["data"]["timings"]
        timezone_name = payload["data"]["meta"].get("timezone", FALLBACK_TIMEZONE)

        times = {}
        for key in PRAYER_KEYS:
            raw = timings[key]  # مثل "04:32 (+03)" أو "04:32"
            times[key] = raw.split(" ")[0]

        return times, timezone_name

    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.error("فشل جلب أوقات الصلاة من Aladhan API: %s - سيتم استخدام الجدول الاحتياطي", e)
        return dict(FALLBACK_TIMES), FALLBACK_TIMEZONE


def _combine_today(time_str: str, timezone_name: str) -> datetime.datetime:
    tz = ZoneInfo(timezone_name)
    now = datetime.datetime.now(tz)
    hour, minute = map(int, time_str.split(":"))
    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)


async def schedule_today_jobs(job_queue: JobQueue) -> None:
    """
    يُستدعى مرة واحدة يوميًا (وأيضًا عند بدء تشغيل البوت) لجلب أوقات اليوم
    وجدولة مهمة نشر واحدة لكل صلاة لم يمضِ وقتها بعد.
    يقبل job_queue مباشرة (وليس context كامل) لتفادي الحاجة لإنشاء
    CallbackContext يدويًا عند استدعائه من post_init عند بدء التشغيل.
    """
    times, timezone_name = await fetch_prayer_times()
    tz = ZoneInfo(timezone_name)
    now = datetime.datetime.now(tz)

    for prayer_key in PRAYER_KEYS:
        run_at = _combine_today(times[prayer_key], timezone_name)
        if run_at <= now:
            logger.info("تخطي صلاة %s لأن وقتها مضى بالفعل اليوم", prayer_key)
            continue

        job_queue.run_once(
            post_scheduled_content,
            when=run_at,
            data={"prayer_key": prayer_key},
            name=f"post_{prayer_key}_{now.date().isoformat()}",
        )
        logger.info("تمت جدولة نشر %s الساعة %s (%s)", prayer_key, run_at.strftime("%H:%M"), timezone_name)


async def post_scheduled_content(context: ContextTypes.DEFAULT_TYPE) -> None:
    """المهمة الفعلية التي تنشر المحتوى في كل القنوات النشطة عند حلول وقت الصلاة."""
    prayer_key = context.job.data["prayer_key"]
    await post_to_all_channels(context, prayer_key)


async def post_to_all_channels(context: ContextTypes.DEFAULT_TYPE, prayer_key: str | None = None) -> dict:
    """
    ينشر حزمة محتوى جديدة في كل القنوات المسجَّلة والنشطة.
    قبل النشر في كل قناة، يعيد التحقق من اشتراك مالكها بالقناة الرسمية
    (تطبيقًا لمبدأ الاشتراك الإجباري الحي - وليس تحققًا لمرة واحدة فقط).
    يرجع ملخصًا بعدد النجاحات والفشل لأغراض أمر /status.
    """
    channel_store = context.bot_data["channel_store"]
    content_manager = context.bot_data["content_manager"]

    channels = channel_store.get_all_active()
    result = {"posted": 0, "skipped_unsubscribed": 0, "failed": 0}

    for channel_id_str, info in channels.items():
        channel_id = int(channel_id_str)
        owner_id = info["owner_user_id"]

        subscribed = await is_user_subscribed(context.bot, owner_id)
        if not subscribed:
            channel_store.deactivate(channel_id, reason="owner_unsubscribed")
            result["skipped_unsubscribed"] += 1
            logger.info("تم تعطيل النشر للقناة %s لأن مالكها لم يعد مشتركًا بالقناة الرسمية", channel_id)
            try:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text=(
                        "⚠️ تم إيقاف النشر في قناتك لأنك لم تعد مشتركًا بالقناة الرسمية.\n"
                        "اشترك من جديد وأرسل /reactivate لإعادة تفعيل النشر."
                    ),
                )
            except Exception:
                pass
            continue

        bundle = content_manager.build_daily_bundle()
        text = format_bundle(bundle, prayer_key=prayer_key)

        try:
            await context.bot.send_message(chat_id=channel_id, text=text)
            result["posted"] += 1
        except Exception as e:
            result["failed"] += 1
            logger.error("فشل النشر في القناة %s: %s", channel_id, e)
            try:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text=f"⚠️ فشل نشر المحتوى في قناتك. السبب التقني: {e}",
                )
            except Exception:
                pass

    return result
