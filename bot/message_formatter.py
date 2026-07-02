"""
وحدة تنسيق الرسالة النهائية التي تُنشر في القناة.
تضع الآية بين قوسين قرآنيين ﴿ ﴾، والذكر/الدعاء بين علامتي تنصيص،
مع إيموجيات هادئة وذكر المصدر بوضوح.
"""

PRAYER_LABELS = {
    "Fajr": "🌅 صلاة الفجر",
    "Dhuhr": "☀️ صلاة الظهر",
    "Asr": "🌤️ صلاة العصر",
    "Maghrib": "🌇 صلاة المغرب",
    "Isha": "🌙 صلاة العشاء",
}


def format_bundle(bundle: dict, prayer_key: str | None = None) -> str:
    verse = bundle["verse"]
    hadith = bundle["hadith"]
    dua_or_azkar = bundle["dua_or_azkar"]
    dua_type = bundle["dua_or_azkar_type"]

    lines = []

    if prayer_key and prayer_key in PRAYER_LABELS:
        lines.append(PRAYER_LABELS[prayer_key])
        lines.append("")

    # الآية القرآنية بين القوسين القرآنيين الرسميين
    lines.append(f"﴿ {verse['text']} ﴾")
    lines.append(f"📖 سورة {verse['surah']} - آية {verse['ayah']}")
    lines.append("")
    lines.append("✨ • ✨ • ✨")
    lines.append("")

    # الحديث/القول بين علامتي تنصيص
    lines.append(f"\u201c{hadith['text']}\u201d")
    lines.append(f"🕊️ {hadith['narrator']} - {hadith['source']}")
    lines.append("")

    # دعاء أو ذكر
    if dua_type == "dua":
        lines.append(f"🤲 \u201c{dua_or_azkar['text']}\u201d")
    else:
        lines.append(f"📿 \u201c{dua_or_azkar['text']}\u201d")
    lines.append("")

    lines.append("اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَآلِ مُحَمَّدٍ 💛")

    return "\n".join(lines)


def format_preview_header(prayer_key: str | None = None) -> str:
    """رسالة توضيحية تُرسل قبل المعاينة في أمر /test الإداري."""
    header = "🔍 هذه معاينة لشكل الرسالة التي سيتم نشرها:\n\n"
    return header
