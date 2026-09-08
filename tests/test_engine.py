"""Engine tests: track gathering, filtering, dedup, caching, countdowns.

Trackers are stubbed so these never touch a network; ``SpaceEngine`` itself is
the real code under test.
"""

from datetime import datetime, timedelta, timezone

from core.cache import EventCache
from engine import SpaceEngine


class _Fake:
    def __init__(self, events):
        self.events = list(events)
        self.fetch_count = 0

    def fetch_timeline_data(self):
        self.fetch_count += 1
        return [dict(e) for e in self.events]


def _mk(time, title, category="EVENT", info="details"):
    return {"time": time, "title": title, "category": category, "info": info}


def _engine(*pairs, cache_file=":memory:"):
    engine = SpaceEngine(cache=EventCache(cache_file, ttl=1800))
    engine.trackers = {name: _Fake(evs) for name, evs in pairs}
    return engine


def _times():
    base = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    return base, base + timedelta(days=1), base + timedelta(days=2)


def test_all_dedupes_identical_probe_events(tmp_path):
    t0, _, _ = _times()
    shared = [_mk(t0, "Falcon 9 : Starlink 6-40")]
    engine = _engine(("probe_launch", shared), ("probe_events", shared),
                     cache_file=str(tmp_path / "c.json"))
    events = engine.get_events(track="all")
    assert len(events) == 1
    assert events[0]["title"] == "Falcon 9 : Starlink 6-40"


def test_dedup_keeps_distinct_events(tmp_path):
    t0, t1, _ = _times()
    engine = _engine(
        ("space_weather", [_mk(t0, "K-Index 5")]),
        ("probe_launch", [_mk(t1, "Falcon 9 : Starlink")]),
        cache_file=str(tmp_path / "c.json"),
    )
    events = engine.get_events(track="all")
    assert {e["title"] for e in events} == {"K-Index 5", "Falcon 9 : Starlink"}


def test_after_before_window_filters(tmp_path):
    t0, t1, t2 = _times()
    engine = _engine(("probe_launch", [_mk(t0, "A"), _mk(t1, "B"), _mk(t2, "C")]),
                     cache_file=str(tmp_path / "c.json"))
    # [] is inclusive on both ends; a 1-hour window around t1 keeps only B.
    events = engine.get_events(track="probe_launch", after=t1, before=t1 + timedelta(hours=1))
    assert [e["title"] for e in events] == ["B"]


def test_name_filter_substring(tmp_path):
    _, t1, _ = _times()
    engine = _engine(
        ("probe_launch", [_mk(t1, "Falcon 9 : Starlink 6-40"), _mk(t1, "Falcon 9 : GPS")]),
        cache_file=str(tmp_path / "c.json"),
    )
    events = engine.get_events(track="probe_launch", name="starlink")
    assert [e["title"] for e in events] == ["Falcon 9 : Starlink 6-40"]


def test_limit_keeps_soonest(tmp_path):
    _, t1, t2 = _times()
    engine = _engine(("probe_launch", [_mk(t1, "Soon"), _mk(t2, "Later")]),
                     cache_file=str(tmp_path / "c.json"))
    events = engine.get_events(track="probe_launch", limit=1)
    assert [e["title"] for e in events] == ["Soon"]


def test_countdown_stamped_on_every_event(tmp_path):
    _, t1, _ = _times()
    engine = _engine(("probe_launch", [_mk(t1, "A")]),
                     cache_file=str(tmp_path / "c.json"))
    events = engine.get_events(track="probe_launch")
    for ev in events:
        assert isinstance(ev.get("countdown"), str) and ev["countdown"]


def test_unknown_track_is_empty(tmp_path):
    engine = _engine(cache_file=str(tmp_path / "c.json"))
    assert engine.get_events(track="nope") == []


def test_cache_serves_second_call(tmp_path):
    _, t1, _ = _times()
    engine = _engine(("probe_launch", [_mk(t1, "A")]),
                     cache_file=str(tmp_path / "c.json"))
    engine.get_events(track="probe_launch")
    engine.get_events(track="probe_launch")
    assert engine.trackers["probe_launch"].fetch_count == 1  # second hit cached