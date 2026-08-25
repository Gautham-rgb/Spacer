"""Tiny TTL JSON cache so the GUI/web don't hammer NOAA + thespacedevs.

Serialises the :data:`core.models.Event`-shaped dicts (which may contain
``datetime`` objects) to JSON and back. Intentionally dependency-free.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

DEFAULT_CACHE_FILE = ".spacer_cache.json"
DEFAULT_TTL = 1800  # 30 minutes


def _serialize(events: list[dict]) -> list[dict]:
    out = []
    for ev in events:
        item = dict(ev)
        t = item.get("time")
        if isinstance(t, datetime):
            item["time"] = t.isoformat()
        out.append(item)
    return out


def _deserialize(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        item = dict(item)
        t = item.get("time")
        if isinstance(t, str):
            try:
                item["time"] = datetime.fromisoformat(t)
            except ValueError:
                item["time"] = datetime.now(timezone.utc)
        out.append(item)
    return out


class EventCache:
    """Filesystem JSON cache with a per-key TTL.

    Used by :class:`~engine.SpaceEngine` so the chat bots, desktop GUI, and web
    app can refresh without re-hitting the upstream APIs on every call.
    """

    def __init__(self, file: str = DEFAULT_CACHE_FILE, ttl: int = DEFAULT_TTL):
        self.file = file
        self.ttl = ttl

    def _read(self) -> dict:
        if not os.path.exists(self.file):
            return {}
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data: dict) -> None:
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass

    @staticmethod
    def make_key(track: str, name: str | None, limit: int | None) -> str:
        return f"{track}|{name or ''}|{limit or ''}"

    def get(self, key: str) -> list[dict] | None:
        data = self._read()
        entry = data.get(key)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > self.ttl:
            return None
        return _deserialize(entry.get("events", []))

    def set(self, key: str, events: list[dict]) -> None:
        data = self._read()
        data[key] = {"ts": time.time(), "events": _serialize(events)}
        self._write(data)

    def clear(self) -> None:
        if os.path.exists(self.file):
            try:
                os.remove(self.file)
            except OSError:
                pass
