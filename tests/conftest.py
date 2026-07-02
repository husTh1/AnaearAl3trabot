"""
يضبط متغيرات بيئة وهمية قبل أي استيراد لوحدات البوت، حتى لا تفشل
عملية جمع الاختبارات (collection) بسبب فحص الإعدادات الإجباري في bot/config.py.
هذا الفحص مقصود ومطلوب في بيئة الإنتاج الفعلية، لكنه يحتاج قيمًا وهمية هنا فقط.
"""
import os
import tempfile

os.environ.setdefault("BOT_TOKEN", "TEST:TOKEN")
os.environ.setdefault("ADMIN_ID", "111111111")
os.environ.setdefault("OFFICIAL_CHANNEL_USERNAME", "test_channel")
os.environ.setdefault("STATE_DIR", tempfile.mkdtemp(prefix="quran_bot_test_state_"))
