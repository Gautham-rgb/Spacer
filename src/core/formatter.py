"""Render ``SpaceEngine`` events as CLI output or Markdown timelines.

The line templates come from ``[tool.spacer.formats]`` in ``pyproject.toml``
(see :mod:`core.pyproject`), with built-in fallbacks so this always works.
Unknown ``{placeholders}`` render as empty strings rather than crashing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console

from core.pyproject import spacer_section
from core.utils import calculate_countdown

_FALLBACK = datetime.min.replace(tzinfo=timezone.utc)
_FORMATS = spacer_section("formats")


class _SafeDefaults(dict):
    """dict for str.format_map: missing keys become empty strings."""

    def __missing__(self, key):
        return ""


def _fmt(template: str, **values: object) -> str:
    return template.format_map(_SafeDefaults(values))


def _sort_key(ev: dict) -> object:
    return ev.get("time") or _FALLBACK


def _when(ev: dict, fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    ev_time = ev.get("time")
    return ev_time.strftime(fmt) if ev_time else "Unknown"


class TimelineFormatter:
    def __init__(self):
        self.console = Console()

    def render_cli(self, events: list) -> None:
        if not events:
            print("No events found for this timeframe.")
            return

        events.sort(key=_sort_key)
        print(f"\n^ {_fmt(_FORMATS['cli_title'])}")
        print("=" * 70)
        for ev in events:
            category_tag = str(ev.get("category", "EVENT")).upper()
            countdown = ev.get("countdown") or calculate_countdown(ev.get("time"))
            print(_fmt(_FORMATS["cli_header"], when=_when(ev), countdown=countdown))
            print(_fmt(_FORMATS["cli_line"],
                       category=category_tag, title=ev.get("title", "Untitled")))
            print(_fmt(_FORMATS["cli_info"], info=(ev.get("info") or "No details.")[:60]))
        print("=" * 70)

    def render_markdown(self, events: list) -> str:
        if not events:
            return "No events found for this timeframe."

        events.sort(key=_sort_key)

        lines = []
        for ev in events:
            category_tag = str(ev.get("category", "EVENT")).upper()
            countdown = ev.get("countdown") or calculate_countdown(ev.get("time"))
            lines.append(_fmt(
                _FORMATS["md_line"],
                category=category_tag,
                title=ev.get("title", "Untitled"),
                when=_when(ev, "%m/%d %H:%M UTC"),
                countdown=countdown,
                info=(ev.get("info") or "No details")[:100],
            ))
        return "\n\n".join(lines)