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
    "*Spacer* commands (prefix with `!space`):\n"
    "• `!space list [track] [--limit N] [--name text]` — list events for a "
    "track (all / space_weather / space_events / probe_launch / probe_events)\n"
    "• `!space weather` — shortcut for space_weather\n"
    "• `!space launches` — shortcut for probe_launch\n"
    "• `!space groq <question>` — ask Spacer a question (`groq reset` clears "
    "the remembered conversation)\n"
    "• `!space update` — check for a new release\n"
    "• `!space version` — print the build\n"
    "• `!space help` — list commands"
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


def _event_embeds(events: list[dict], limit: int = 20,
                  summary: str | None = None) -> list[dict]:
    from core.utils import calculate_countdown

    embeds: list[dict] = []
    if summary:
        embeds.append({"title": summary, "color": 0x2B6CB0,
                       "description": "_Events matching your filters._"})
    if not events:
        embeds.append({"title": "Nothing scheduled in this window.",
                       "description": "_Try clearing the filters or widening the date range._",
                       "color": 0x888888})
        return embeds
    cap = min(max(limit, 1), 10)
    shown = sorted(events, key=lambda e: e.get("time") or 0)[:cap]
    for ev in shown:
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
    if len(events) > cap:
        embeds.append({"title": f"… and {len(events) - cap} more",
                       "description": "Listed first by time; use a lower "
                                      "--limit to show fewer.",
                       "color": 0x888888})
    return embeds


def dispatch(engine: SpaceEngine, cmd: str,
             context: dict | None = None) -> CommandResult:
    """Route a ``!space`` command string to its :class:`CommandResult`.

    Handles the shortcuts (``weather``/``launches``), tracks a ``list`` target
    wherever it appears, and picks up ``--limit`` / ``--name`` flags so the
    bots behave like the CLI/web/GUI. ``context`` (e.g. ``{"channel": ...,
    "user": ...}``) scopes the ``!space groq`` conversation memory per room.
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

    if sub == "groq":
        return _groq_result(cmd, context)

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

    summary = f"Spacer timeline ({track})"
    chips = [piece for piece in (f"name “{name}”" if name else None,
                                 f"limit {limit}" if limit is not None else None)
             if piece]
    if chips:
        summary += " · " + " · ".join(chips)
    return CommandResult(summary, _slack_blocks(events, limit=limit, summary=summary),
                         _event_embeds(events, limit=limit, summary=summary))


def _help_result() -> CommandResult:
    return CommandResult(HELP_TEXT,
                         [{"type": "section",
                           "text": {"type": "mrkdwn", "text": HELP_TEXT}}],
                         [{"title": "Spacer", "description": HELP_TEXT, "color": 0x2B6CB0}])


def _conversation_key(context: dict | None) -> str:
    if not context:
        return "shared"
    return f"{context.get('user') or '?'}@{context.get('channel') or '?'}"


def _groq_result(cmd: str, context: dict | None) -> CommandResult:
    """Handle ``!space groq <question>`` (and ``reset``) with per-room memory."""
    from core.groq_chat import clear_conversation, groq_chat

    question = cmd[len("groq"):].strip()
    key = _conversation_key(context)
    if question.lower() in ("reset", "clear"):
        clear_conversation(key)
        msg = "Conversation cleared."
    elif not question:
        msg = "Ask me something, e.g. `!space groq when is the next launch?`"
    else:
        msg = groq_chat(question, key=key)
        # Slack mrkdwn sections cap at 3000 chars; keep the reply sendable.
        if len(msg) > 2900:
            msg = msg[:2900].rstrip() + "\n… (truncated)"
    return CommandResult(msg,
                         [{"type": "section",
                           "text": {"type": "mrkdwn", "text": msg}}],
                         [{"title": "Spacer groq", "description": msg, "color": 0x2B6CB0}])


def _slack_blocks(events: list[dict], limit: int = 20,
                  summary: str | None = None) -> list[dict]:
    from core.utils import calculate_countdown

    blocks: list[dict] = [{
        "type": "header",
        "text": {"type": "plain_text", "text": summary or "Upcoming space events"},
    }]
    if not events:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_No events found for this timeframe._"},
        })
        return blocks
    cap = min(max(limit, 1), 25)
    shown = sorted(events, key=lambda e: e.get("time") or 0)[:cap]
    for ev in shown:
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
    if len(events) > cap:
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn",
                                "text": f"… and `{len(events) - cap}` more — cap "
                                        "the list with `--limit N`."}})
    return blocks
