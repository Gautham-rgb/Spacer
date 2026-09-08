"""Tiny TTL JSON cache round-trips."""

import time
from datetime import datetime, timezone

from core.cache import EventCache


def test_round_trip_keeps_datetimes(tmp_path):
    cache = EventCache(str(tmp_path / "c.json"), ttl=1800)
    key = EventCache.make_key("probe_launch", "falcon", 5)
    when = datetime(2026, 9, 12, 3, 30, tzinfo=timezone.utc)
    cache.set(key, [{"title": "Falcon 9", "time": when, "category": "Probe"}])
    events = cache.get(key)
    assert events is not None
    assert events[0]["title"] == "Falcon 9"
    assert events[0]["time"] == when


def test_expired_entry_is_miss(tmp_path):
    cache = EventCache(str(tmp_path / "c.json"), ttl=0)
    key = EventCache.make_key("space_weather", None, 10)
    cache.set(key, [{"title": "x", "time": datetime.now(timezone.utc)}])
    assert cache.get(key) is None


def test_stats_reports_entries(tmp_path):
    cache = EventCache(str(tmp_path / "c.json"), ttl=1800)
    cache.set(EventCache.make_key("all", None, 20), [{"title": "a"}])
    stats = cache.stats()
    assert stats["file"] == str(tmp_path / "c.json")
    assert stats["entries"]["all||20"]["events"] == 1
    assert "age_s" in stats["entries"]["all||20"]


def test_clear_removes_file(tmp_path):
    cache = EventCache(str(tmp_path / "c.json"), ttl=1800)
    cache.set("k", [{"title": "a"}])
    assert (tmp_path / "c.json").exists()
    cache.clear()
    assert not (tmp_path / "c.json").exists()