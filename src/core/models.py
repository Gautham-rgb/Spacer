from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class Event(TypedDict, total=False):
    """Stable shape returned by ``SpaceEngine.get_events``.

    UIs (CLI, chat bots, desktop GUI, web) should rely on these keys and nothing
    else. ``time`` and ``category``/``title``/``info`` are the core fields; the
    rest are optional enrichment that front-ends may ignore.
    """

    time: datetime
    category: str
    title: str
    info: str
    source: str
    url: str
    separation_deg: float
    countdown: str


def build_event(*, time: datetime, category: str, title: str, info: str,
                source: str = "", url: str = "",
                separation_deg: float | None = None) -> "Event":
    ev: Event = {
        "time": time,
        "category": category,
        "title": title,
        "info": info,
    }
    if source:
        ev["source"] = source
    if url:
        ev["url"] = url
    if separation_deg is not None:
        ev["separation_deg"] = separation_deg
    return ev
