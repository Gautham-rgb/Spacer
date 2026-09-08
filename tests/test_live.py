"""End-to-end smoke against the real engine and real upstream APIs.

Opt-in via ``-m live``: these hit NOAA + thespacedevs and may download the
Skyfield ephemeris on first run, so they are slow and need a network.
"""

import pytest

from engine import SpaceEngine

TRACKS_TO_CHECK = ["space_weather", "space_events", "probe_launch", "probe_events"]


@pytest.mark.live
@pytest.mark.parametrize("track", TRACKS_TO_CHECK)
def test_live_track_returns_shaped_events(track):
    engine = SpaceEngine()
    events = engine.get_events(track=track, limit=5, use_cache=False)
    for ev in events:
        assert ev.get("title")
        assert ev.get("time") is not None
        assert ev.get("countdown")
        assert "category" in ev


@pytest.mark.live
def test_live_all_has_no_duplicate_titles():
    engine = SpaceEngine()
    titles = [ev["title"] for ev in engine.get_events("all", limit=30, use_cache=False)]
    assert len(titles) == len(set(titles))