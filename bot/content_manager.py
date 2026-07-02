"""
وحدة إدارة المحتوى الديني (آيات، أحاديث، أدعية، أذكار).
تضمن عدم تكرار نفس العنصر قبل استنفاد كامل القائمة، وعند الاستنفاد تبدأ دورة جديدة.
"""
import json
import os
import random
from bot.config import DATA_DIR
from bot.storage import ContentStateStore

CATEGORIES = {
    "quran": "quran_verses.json",
    "hadith": "ahadith.json",
    "dua": "duas.json",
    "azkar": "azkar.json",
}


class ContentManager:
    def __init__(self, state_store: ContentStateStore, data_dir: str = DATA_DIR):
        self.state_store = state_store
        self._content = {}
        for category, filename in CATEGORIES.items():
            self._content[category] = self._load_file(os.path.join(data_dir, filename))

    @staticmethod
    def _load_file(path: str) -> list:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not items:
            raise ValueError(f"ملف المحتوى فارغ: {path}")
        return items

    def pick_next(self, category: str) -> dict:
        """
        يختار عنصرًا عشوائيًا من الفئة المطلوبة لم يُنشر مؤخرًا.
        إذا استُنفدت كل العناصر، يبدأ دورة جديدة (يعيد التدوير) تلقائيًا.
        """
        if category not in self._content:
            raise ValueError(f"فئة محتوى غير معروفة: {category}")

        items = self._content[category]
        used_ids = set(self.state_store.get_used_ids(category))
        available = [item for item in items if item["id"] not in used_ids]

        if not available:
            # استُنفدت كل العناصر - نبدأ دورة جديدة بدل التوقف عن النشر
            self.state_store.reset_category(category)
            available = items

        chosen = random.choice(available)
        self.state_store.mark_used(category, chosen["id"])
        return chosen

    def build_daily_bundle(self) -> dict:
        """
        يبني حزمة محتوى واحدة (آية + حديث + دعاء أو ذكر بالتناوب) لرسالة نشر واحدة.
        """
        verse = self.pick_next("quran")
        hadith = self.pick_next("hadith")
        # نتناوب بين الأدعية والأذكار لتنويع الرسالة
        dua_or_azkar_category = random.choice(["dua", "azkar"])
        dua_or_azkar = self.pick_next(dua_or_azkar_category)

        return {
            "verse": verse,
            "hadith": hadith,
            "dua_or_azkar": dua_or_azkar,
            "dua_or_azkar_type": dua_or_azkar_category,
        }
