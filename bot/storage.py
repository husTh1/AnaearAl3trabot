"""
تخزين بسيط باستخدام ملفات JSON - بدون أي قاعدة بيانات.
مناسب لأن المحتوى الديني ثابت، والبيانات المخزَّنة هنا (القنوات المسجَّلة
ومؤشر آخر المحتوى المنشور) صغيرة الحجم ولا تحتاج محرك قواعد بيانات.

ملاحظة مهمة للنشر على Railway:
يجب أن يشير STATE_DIR إلى Volume دائم، وإلا سيتم فقدان هذه الملفات
عند كل إعادة نشر (redeploy) لأن نظام الملفات في Railway غير دائم افتراضيًا.
"""
import json
import os
import threading
from typing import Any

_lock = threading.Lock()


def _read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        # ملف تالف أو غير قابل للقراءة - نرجع للقيمة الافتراضية بدل تعطيل البوت بالكامل
        return default


def _write_json(path: str, data: Any) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)  # كتابة ذرية (atomic) لتفادي تلف الملف عند انقطاع مفاجئ


class ChannelStore:
    """يدير قائمة القنوات المسجَّلة (channel_id -> بيانات القناة)."""

    def __init__(self, path: str):
        self.path = path

    def _load(self) -> dict:
        return _read_json(self.path, default={})

    def _save(self, data: dict) -> None:
        _write_json(self.path, data)

    def register(self, channel_id: int, owner_user_id: int, channel_title: str) -> None:
        with _lock:
            data = self._load()
            data[str(channel_id)] = {
                "owner_user_id": owner_user_id,
                "channel_title": channel_title,
                "active": True,
            }
            self._save(data)

    def deactivate(self, channel_id: int, reason: str = "") -> None:
        with _lock:
            data = self._load()
            key = str(channel_id)
            if key in data:
                data[key]["active"] = False
                data[key]["deactivation_reason"] = reason
                self._save(data)

    def reactivate(self, channel_id: int) -> None:
        with _lock:
            data = self._load()
            key = str(channel_id)
            if key in data:
                data[key]["active"] = True
                data[key].pop("deactivation_reason", None)
                self._save(data)

    def remove(self, channel_id: int) -> None:
        with _lock:
            data = self._load()
            data.pop(str(channel_id), None)
            self._save(data)

    def get_all_active(self) -> dict:
        data = self._load()
        return {k: v for k, v in data.items() if v.get("active")}

    def get_all(self) -> dict:
        return self._load()

    def get_by_owner(self, owner_user_id: int) -> dict:
        data = self._load()
        return {k: v for k, v in data.items() if v.get("owner_user_id") == owner_user_id}


class ContentStateStore:
    """يتتبّع أي عناصر محتوى (آيات/أحاديث/أدعية/أذكار) نُشرت مسبقًا لتفادي التكرار."""

    def __init__(self, path: str):
        self.path = path

    def _load(self) -> dict:
        return _read_json(self.path, default={"used": {}})

    def _save(self, data: dict) -> None:
        _write_json(self.path, data)

    def get_used_ids(self, category: str) -> list:
        data = self._load()
        return data.get("used", {}).get(category, [])

    def mark_used(self, category: str, item_id: str) -> None:
        with _lock:
            data = self._load()
            data.setdefault("used", {}).setdefault(category, [])
            if item_id not in data["used"][category]:
                data["used"][category].append(item_id)
            self._save(data)

    def reset_category(self, category: str) -> None:
        with _lock:
            data = self._load()
            data.setdefault("used", {})[category] = []
            self._save(data)
