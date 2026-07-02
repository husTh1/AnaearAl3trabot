import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.message_formatter import format_bundle, PRAYER_LABELS


def _sample_bundle(dua_type="dua"):
    return {
        "verse": {"id": "q001", "surah": "البقرة", "ayah": 286, "text": "نص الآية التجريبية"},
        "hadith": {"id": "h001", "text": "نص الحديث التجريبي", "narrator": "الإمام علي عليه السلام", "source": "نهج البلاغة"},
        "dua_or_azkar": {"id": "d001", "text": "نص الدعاء التجريبي"},
        "dua_or_azkar_type": dua_type,
    }


def test_verse_wrapped_in_quranic_brackets():
    text = format_bundle(_sample_bundle())
    assert "﴿ نص الآية التجريبية ﴾" in text


def test_hadith_wrapped_in_quotes():
    text = format_bundle(_sample_bundle())
    assert "\u201cنص الحديث التجريبي\u201d" in text


def test_narrator_and_source_present():
    text = format_bundle(_sample_bundle())
    assert "الإمام علي عليه السلام" in text
    assert "نهج البلاغة" in text


def test_surah_and_ayah_reference_present():
    text = format_bundle(_sample_bundle())
    assert "سورة البقرة" in text
    assert "286" in text


def test_prayer_label_included_when_provided():
    text = format_bundle(_sample_bundle(), prayer_key="Fajr")
    assert PRAYER_LABELS["Fajr"] in text


def test_no_prayer_label_when_not_provided():
    text = format_bundle(_sample_bundle(), prayer_key=None)
    for label in PRAYER_LABELS.values():
        assert label not in text


def test_dua_uses_dua_emoji_and_azkar_uses_azkar_emoji():
    dua_text = format_bundle(_sample_bundle(dua_type="dua"))
    azkar_text = format_bundle(_sample_bundle(dua_type="azkar"))
    assert "🤲" in dua_text
    assert "📿" in azkar_text
