"""Web app for Spacer, built with NiceGUI (hosted on Hack Club Nest).

Wraps ``SpaceEngine.get_events`` in a NiceGUI page: track selector, date
range, name + limit inputs, and a live timeline. Because the desktop GUI also
uses NiceGUI-native widgets, the two front-ends can share rendering helpers.

Nest/HF-style hosting: bind to ``0.0.0.0`` on the ``PORT`` env var. The
repo-root ``app.py`` imports and runs this so the platform can boot it as a
plain ASGI/process.

Per the roadmap (Phase 2) this web app, the ttk desktop GUI, and the CLI all
consume the same headless engine — no fetching logic is duplicated here.
"""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime, timezone

from engine import SpaceEngine
from version import __version__

TRACKS = ["all", "space_weather", "space_events", "probe_launch", "probe_events"]

# The site name — used for the browser tab title and the page heading.
SITE_NAME = "Spacer"


def build_event_cards(container, events: list[dict]) -> None:
    from nicegui import ui

    container.clear()
    if not events:
        with container:
            ui.label("Nothing scheduled in this window.").classes("text-gray-500")
        return
    with container:
        for ev in sorted(events, key=lambda e: e.get("time") or 0):
            ev_time = ev.get("time")
            ts = ev_time.strftime("%Y-%m-%d %H:%M UTC") if ev_time else "Unknown"
            countdown = ev.get("countdown") or "T-?"
            with ui.card().classes("w-full no-shadow border"):
                with ui.row().classes("items-baseline justify-between"):
                    ui.label(str(ev.get("title", "Untitled"))).classes("text-base font-semibold")
                    ui.label(str(ev.get("category", "EVENT")).upper()).classes(
                        "text-xs text-gray-400 tracking-wide")
                ui.label(ev.get("info", "No details")).classes("text-sm text-gray-600")
                ui.label(f"{ts} · {countdown}").classes("text-xs text-gray-400")


def create_app(engine: SpaceEngine | None = None):
    from nicegui import ui

    engine = engine or SpaceEngine()

    ui.label(SITE_NAME).classes("text-3xl font-bold tracking-tight")
    ui.label("Upcoming space weather, launches, and sky alignments.").classes("text-sm text-gray-500")

    from core.updates import check_for_update
    ui.label(check_for_update()).classes("text-xs text-gray-400")

    track = ui.select(TRACKS, value="all", label="Track")
    with ui.row():
        after = ui.input("After (YYYY-MM-DD)")
        before = ui.input("Before (YYYY-MM-DD)")
        name = ui.input("Name filter")
        limit = ui.number("Limit", value=20, min=1, max=200)

    status = ui.label("")
    results = ui.column().classes("w-full gap-2")

    def _parse(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def refresh() -> None:
        status.set_text("Fetching space data...")
        events = engine.get_events(
            track=track.value,
            after=_parse(after.value),
            before=_parse(before.value),
            name=name.value or None,
            limit=int(limit.value or 20),
        )
        build_event_cards(results, events)
        status.set_text(f"Showing {len(events)} event(s).")

    ui.button("Refresh", on_click=refresh).classes("mt-2")
    refresh()

    # --- Groq chat ---
    from core.groq_chat import groq_chat

    with ui.card().classes("w-full no-shadow border mt-4"):
        ui.label("Ask Groq").classes("text-lg font-semibold")
        ui.label("Powered by Groq — ask anything.").classes("text-xs text-gray-400")
        groq_input = ui.input("Your question").classes("w-full")
        groq_out = ui.label("").style("white-space: pre-wrap")
        groq_out.classes("text-sm")

        async def _ask_groq() -> None:
            prompt = (groq_input.value or "").strip()
            if not prompt:
                groq_out.set_text("Type a question first.")
                return
            groq_out.set_text("Thinking…")
            answer = await asyncio.to_thread(groq_chat, prompt)
            groq_out.set_text(answer)

        ui.button("Ask", on_click=_ask_groq).classes("mt-2")

    return ui


def _start_bots() -> None:
    """Launch the chat bots in background threads (server-friendly).

    The web server owns the main thread; the Slack/Discord bots each run their
    own blocking loop in a daemon thread. Tokens are read from the environment,
    so a bot simply doesn't start if its credentials are absent — the server
    keeps serving the web app either way.
    """
    if os.environ.get("SLACK_BOT_TOK") and os.environ.get("SLACK_APP_TOK"):
        from core.slack_bot import SlackBot
        threading.Thread(target=lambda: SlackBot().run(), daemon=True).start()
    if os.environ.get("DISCORD_BOT_TOK"):
        from core.discord_bot import DiscordBot
        threading.Thread(target=lambda: DiscordBot().run(), daemon=True).start()


def serve() -> None:
    """Run the web app and the chat bots together on one server.

    Binds NiceGUI to ``0.0.0.0:$PORT`` (Hack Club Nest / HF Spaces) and starts
    any configured chat bots in the background. This is the entry point used by
    the repo-root ``app.py`` and the ``spacer-serve`` script.
    """
    _start_bots()
    from nicegui import ui

    create_app()
    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        show=False,
        title=SITE_NAME,
    )


def main() -> None:
    from nicegui import ui

    create_app()
    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        show=False,
        title=SITE_NAME,
    )


if __name__ == "__main__":
    main()
