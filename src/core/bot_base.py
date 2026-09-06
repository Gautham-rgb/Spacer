"""Shared command handling for the Spacer chat bots.

Both the Slack (Socket Mode) and Discord (discord.py) front-ends share the
same command vocabulary (``list``, ``weather``, ``launches``, ``version``,
``help``). This module owns that logic and returns a platform-neutral payload
that each adapter renders in its own native format (Block Kit vs Embeds).
"""

from __future__ import annotations

from engine import SpaceEngine
from core.config import TRACKS
from version import __version__

HELP_TEXT = (
    "*Spacer* — what you can ask (prefix with `!space`)\n"
    "• `!space list [track] [--limit N] [--name text]` — events for a track "
    "(all / space_weather / space_events / probe_launch / probe_events)\n"
    "• `!space weather` — space-weather only\n"
    "• `!space launches` — upcoming launches\n"
    "• `!space update` — check if a newer release is out\n"
    "• `!space version` — which build this is\n"
    "• `!space help` — this message"
)

_TRACK_ALIASES = {
    "weather": "space_weather",
    "launches": "probe_launch",
    "launch": "probe_launch",
}


class CommandResult:
    """Platform-neutral response produced by :func:`dispatch`."""

    def __init__(self, plain: str, slack_blocks: list[dict], discord_embeds: list[dict]):
        self.plain = plain
        self.slack_blocks = slack_blocks
        self.discord_embeds = discord_embeds


def _event_embeds(events: list[dict]) -> list[dict]:
    from core.utils import calculate_countdown

    if not events:
        return [{"title": "Upcoming space events",
                 "description": "_Nothing scheduled in this window._",
                 "color": 0x888888}]
    embeds: list[dict] = []
    for ev in sorted(events, key=lambda e: e.get("time") or 0)[:20]:
        ev_time = ev.get("time")
        ts = ev_time.strftime("%Y-%m-%d %H:%M UTC") if ev_time else "Unknown"
        countdown = ev.get("countdown") or calculate_countdown(ev_time)
        embeds.append({
            "title": ev.get("title", "Untitled"),
            "description": ev.get("info") or "No details",
            "color": 0x2B6CB0,
            "fields": [
                {"name": "Category", "value": str(ev.get("category", "EVENT")).upper(),
                 "inline": True},
                {"name": "When", "value": f"{ts} ({countdown})", "inline": True},
            ],
        })
    return embeds


def dispatch(engine: SpaceEngine, cmd: str) -> CommandResult:
    """Route a ``!space`` command string to its :class:`CommandResult`.

    Handles the shortcuts (``weather``/``launches``), tracks a ``list`` target
    wherever it appears, and picks up ``--limit`` / ``--name`` flags so the
    bots behave like the CLI/web/GUI.
    """
    parts = cmd.split()
    if not parts:
        return _help_result()

    sub = parts[0].lower()
    if sub in ("help", "h"):
        return _help_result()

    if sub == "version":
        msg = f"Spacer v{__version__}"
        return CommandResult(msg,
                             [{"type": "section",
                               "text": {"type": "mrkdwn", "text": msg}}],
                             [{"title": "Spacer", "description": msg, "color": 0x2B6CB0}])

    if sub == "update":
        from core.updates import check_for_update
        msg = check_for_update()
        return CommandResult(msg,
                             [{"type": "section",
                               "text": {"type": "mrkdwn", "text": msg}}],
                             [{"title": "Spacer update", "description": msg, "color": 0x2B6CB0}])

    known = set(_TRACK_ALIASES) | set(TRACKS)
    track = _TRACK_ALIASES.get(sub, sub if sub in TRACKS else "all")
    limit = 20
    name: str | None = None

    text_tokens: list[str] = []
    i = 1
    while i < len(parts):
        tok = parts[i]
        if tok in ("-l", "--limit") and i + 1 < len(parts):
            try:
                limit = max(1, int(parts[i + 1]))
            except ValueError:
                pass
            i += 2
            continue
        if tok in ("-n", "--name") and i + 1 < len(parts):
            name = parts[i + 1]
            i += 2
            continue
        text_tokens.append(tok)
        i += 1

    for tok in text_tokens:
        low = tok.lower()
        if low in known:
            track = _TRACK_ALIASES.get(low, low)
            break

    events = engine.get_events(track=track, name=name, limit=limit)
    plain = f"Spacer timeline ({track})"
    if name:
        plain += f" — “{name}”"
    return CommandResult(plain, _slack_blocks(events), _event_embeds(events))


def _help_result() -> CommandResult:
    return CommandResult(HELP_TEXT,
                         [{"type": "section",
                           "text": {"type": "mrkdwn", "text": HELP_TEXT}}],
                         [{"title": "Spacer", "description": HELP_TEXT, "color": 0x2B6CB0}])


def _slack_blocks(events: list[dict]) -> list[dict]:
    from core.utils import calculate_countdown

    blocks: list[dict] = [{
        "type": "header",
        "text": {"type": "plain_text", "text": "Upcoming space events"},
    }]
    if not events:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No events found for this timeframe._"},
        })
        return blocks
    for ev in sorted(events, key=lambda e: e.get("time") or 0)[:20]:
        ev_time = ev.get("time")
        ts = ev_time.strftime("%Y-%m-%d %H:%M UTC") if ev_time else "Unknown"
        countdown = ev.get("countdown") or calculate_countdown(ev_time)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (f"*{ev.get('title', 'Untitled')}*  "
                         f"`[{str(ev.get('category', 'EVENT')).upper()}]`\n"
                         f"{ev.get('info') or 'No details'}\n"
                         f"`{ts}`  ({countdown})"),
            },
        })
    return blocks
