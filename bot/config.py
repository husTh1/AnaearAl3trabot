"""
إعدادات البوت - كل الإعدادات الحساسة تُقرأ من متغيرات البيئة فقط.
لا يوجد أي توكن أو معرف مكتوب مباشرة داخل الكود.
"""
import os
import logging
from dotenv import load_dotenv

# يحمّل القيم من ملف .env الموجود في مجلد المشروع (إن وُجد) إلى متغيرات البيئة.
# على الاستضافات مثل Railway، لا يوجد ملف .env أصلًا والمتغيرات تُضبط مباشرة
# من لوحة التحكم، لذا هذا السطر لا يسبب أي مشكلة هناك (لن يجد ملفًا فيتجاهله بصمت).
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("quran_bot")


class ConfigError(Exception):
    """خطأ في الإعدادات - يوقف تشغيل البوت فورًا بدل الاستمرار بشكل غير آمن."""
    pass


def _get_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"متغير البيئة المطلوب '{name}' غير موجود. "
            f"يرجى ضبطه قبل تشغيل البوت (راجع ملف .env.example)."
        )
    return value


def _get_optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# --- إعدادات أساسية إجبارية ---
BOT_TOKEN = _get_required("BOT_TOKEN")
ADMIN_ID = int(_get_required("ADMIN_ID"))

# القناة الرسمية الإجبارية للاشتراك (بدون علامة @) - مثال: forca91
OFFICIAL_CHANNEL_USERNAME = _get_required("OFFICIAL_CHANNEL_USERNAME").lstrip("@")

# --- إعدادات اختيارية ---
# مجلد تخزين ملفات الحالة (يجب أن يشير إلى Volume دائم على Railway)
STATE_DIR = _get_optional("STATE_DIR", default="./state")

# إحداثيات دقيقة لحساب أوقات الصلاة (مركز بغداد افتراضيًا) - منهج الشيعة الاثنا عشرية Aladhan method=0
# استخدام إحداثيات مباشرة بدل اسم مدينة نصي يزيل خطوة "ترجمة الاسم لإحداثيات" الوسيطة من حساب Aladhan،
# فيصبح الحساب مباشرًا وأدق.
PRAYER_LATITUDE = float(_get_optional("PRAYER_LATITUDE", default="33.3152"))
PRAYER_LONGITUDE = float(_get_optional("PRAYER_LONGITUDE", default="44.3661"))
ALADHAN_METHOD = _get_optional("ALADHAN_METHOD", default="0")  # 0 = Shia Ithna-Ashari

# اسم قناة النشر الافتراضية الثابتة (اختياري - إن أردت قناة واحدة فقط بدل تعدد القنوات)
FIXED_TARGET_CHANNEL = _get_optional("FIXED_TARGET_CHANNEL", default="")

os.makedirs(STATE_DIR, exist_ok=True)

CHANNELS_FILE = os.path.join(STATE_DIR, "channels.json")
CONTENT_STATE_FILE = os.path.join(STATE_DIR, "content_state.json")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
