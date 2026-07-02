import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.content_manager import ContentManager
from bot.storage import ContentStateStore


def _build_manager(tmp_dir: str) -> ContentManager:
    state_path = os.path.join(tmp_dir, "content_state.json")
    store = ContentStateStore(state_path)
    return ContentManager(store)


def test_pick_next_no_repeats_within_one_cycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = _build_manager(tmp_dir)
        total_verses = len(manager._content["quran"])

        seen_ids = set()
        for _ in range(total_verses):
            item = manager.pick_next("quran")
            assert item["id"] not in seen_ids, "تم اختيار نفس الآية مرتين قبل استنفاد القائمة الكاملة"
            seen_ids.add(item["id"])

        assert len(seen_ids) == total_verses


def test_pick_next_resets_cycle_after_exhaustion():
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = _build_manager(tmp_dir)
        total_hadith = len(manager._content["hadith"])

        for _ in range(total_hadith):
            manager.pick_next("hadith")

        # بعد استنفاد كل الأحاديث، يجب أن تستمر الدالة بالعمل (تبدأ دورة جديدة) بدل رمي خطأ
        next_item = manager.pick_next("hadith")
        assert next_item is not None
        assert "id" in next_item


def test_build_daily_bundle_has_all_parts():
    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = _build_manager(tmp_dir)
        bundle = manager.build_daily_bundle()

        assert "verse" in bundle
        assert "hadith" in bundle
        assert "dua_or_azkar" in bundle
        assert bundle["dua_or_azkar_type"] in ("dua", "azkar")
        assert bundle["verse"]["text"]
        assert bundle["hadith"]["text"]


def test_all_content_files_have_required_fields():
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    required_fields = {
        "quran_verses.json": {"id", "surah", "ayah", "text"},
        "ahadith.json": {"id", "text", "narrator", "source"},
        "duas.json": {"id", "text", "source"},
        "azkar.json": {"id", "text"},
    }
    for filename, fields in required_fields.items():
        path = os.path.join(data_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        assert len(items) > 0, f"{filename} فارغ"
        seen_ids = set()
        for item in items:
            assert fields.issubset(item.keys()), f"عنصر ناقص الحقول في {filename}: {item}"
            assert item["id"] not in seen_ids, f"معرف مكرر في {filename}: {item['id']}"
            seen_ids.add(item["id"])
