import os
import sys
import datetime

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import scheduler


def test_combine_today_produces_correct_hour_minute():
    dt = scheduler._combine_today("14:35", "Asia/Baghdad")
    assert dt.hour == 14
    assert dt.minute == 35
    assert dt.tzinfo is not None


class _FakeResponse:
    def __init__(self, payload, status_ok=True):
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        return _FakeAsyncClient.response


@pytest.mark.asyncio
async def test_fetch_prayer_times_parses_valid_response(monkeypatch):
    fake_payload = {
        "data": {
            "timings": {
                "Fajr": "04:32 (+03)",
                "Dhuhr": "12:31 (+03)",
                "Asr": "16:05 (+03)",
                "Maghrib": "19:20 (+03)",
                "Isha": "20:50 (+03)",
            },
            "meta": {"timezone": "Asia/Baghdad"},
        }
    }
    _FakeAsyncClient.response = _FakeResponse(fake_payload)
    monkeypatch.setattr(scheduler.httpx, "AsyncClient", _FakeAsyncClient)

    times, tz_name = await scheduler.fetch_prayer_times()

    assert times["Fajr"] == "04:32"
    assert times["Dhuhr"] == "12:31"
    assert tz_name == "Asia/Baghdad"


@pytest.mark.asyncio
async def test_fetch_prayer_times_falls_back_on_error(monkeypatch):
    class _RaisingClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, params=None):
            raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(scheduler.httpx, "AsyncClient", _RaisingClient)

    times, tz_name = await scheduler.fetch_prayer_times()

    assert times == scheduler.FALLBACK_TIMES
    assert tz_name == scheduler.FALLBACK_TIMEZONE
