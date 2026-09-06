"""Web app for Spacer, built with NiceGUI (hosted on Hack Club Nest).

Routes:
  /                      Home page: four big buttons, one per data track.
  /tracks/{track}        Timeline for one track (clickable event cards).
  /event/{track}/{eid}  Detail page for a single event (stable content id).

``create_app()`` returns the root page callback for NiceGUI 3.x (``ui.run``
accepts a ``root`` callable since 3.0.0). Extra pages are registered with
``@ui.page`` so the console-script entry point (which imports this module and
re-runs it) does not crash the auto-index fallback.

Nest/HF-style hosting: bind to ``0.0.0.0`` on the ``PORT`` env var.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import threading
import time
from datetime import datetime, timezone
from nicegui import ui
from core.config import TRACK_NAMES
from core.updates import check_for_update
from engine import SpaceEngine
from version import __version__

SITE_NAME = "Spacer"

# Dark-space palette.
BG_COLOR = "#070b16"
PANEL_COLOR = "#0e1526"
BORDER_COLOR = "#1d2839"
ACCENT = "#5898d4"

# Home-page track cards, keyed by the canonical track names from config.
_TRACK_META = {
    "space_weather": {"label": "Space Weather", "icon": "storm",
                      "desc": "Solar storms and K-index forecasts from NOAA."},
    "space_events": {"label": "Planetary Alignments", "icon": "auto_awesome",
                     "desc": "Conjunctions and 180° alignments of the planets."},
    "probe_launch": {"label": "Rocket Launches", "icon": "rocket_launch",
                     "desc": "Upcoming launches from around the world."},
    "probe_events": {"label": "Probe Missions", "icon": "satellite_alt",
                     "desc": "Missions and probes on their way through space."},
}
TRACK_CARDS = [
    {"track": name, **_TRACK_META.get(name, {"label": name, "icon": "star", "desc": ""})}
    for name in TRACK_NAMES
]

# Category -> (tag color, accent) for consistent theming.
CATEGORY_STYLE: dict[str, tuple[str, str]] = {
    "space_weather": ("#0d3b66", "#f4d35e"),
    "space_events": ("#22577a", "#38a3a5"),
    "PLANETARY": ("#22577a", "#38a3a5"),
    "probe_launch": ("#4a1942", "#ee6c4d"),
    "probe_events": ("#240046", "#c77dff"),
    "Probe": ("#240046", "#c77dff"),
    "NOAA_FORECAST": ("#0d3b66", "#57cc99"),
    "NOAA_PAST": ("#2d3142", "#adb5bd"),
}
DEFAULT_CAT = ("#1f2738", "#7f8ea3")

_ENGINE: SpaceEngine | None = None


def _get_engine() -> SpaceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = SpaceEngine()
    return _ENGINE


# PyPI update check is a blocking urllib call with a 5s timeout on a cold
# network. Calling it on every page render would stall every page build, so
# memoize the result for a few hours (module-level, shared by all clients).
_UPDATE_MSG: str | None = None
_UPDATE_TS = 0.0
_UPDATE_TTL = 6 * 3600


def _update_status() -> str:
    global _UPDATE_MSG, _UPDATE_TS
    now = time.time()
    if _UPDATE_MSG is None or now - _UPDATE_TS > _UPDATE_TTL:
        _UPDATE_MSG = check_for_update()
        _UPDATE_TS = now
    return _UPDATE_MSG


def _cat_style(category: str | None) -> tuple[str, str]:
    return CATEGORY_STYLE.get(str(category or "").strip(), DEFAULT_CAT)


def _track_events(track: str, limit: int = 300) -> list[dict]:
    events = _get_engine().get_events(track=track, limit=limit)
    return sorted(events, key=lambda e: e.get("time") or datetime.min.replace(tzinfo=timezone.utc))


def _event_id(ev: dict) -> str:
    """Stable short id for an event, immune to list filtering/reordering."""
    raw = "|".join(str(ev.get(k, "")) for k in ("time", "title", "info"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _page_setup() -> None:
    """Common dark-mode + global CSS applied by every page."""
    ui.dark_mode().enable()
    ui.add_head_html(
        f"""
        <style>
          html, body {{ background: {BG_COLOR}; }}
          body {{ background:
            radial-gradient(1200px 600px at 80% -10%, #12203a 0%, transparent 60%),
            radial-gradient(900px 500px at -10% 110%, #101a2e 0%, transparent 55%),
            {BG_COLOR}; }}
          .nicegui-content {{ max-width: 900px; margin: 0 auto; padding: 24px 16px; }}
          a {{ color: {ACCENT}; }}
        </style>
        """
    )


def _header(title: str = SITE_NAME, back_to: str | None = None) -> None:
    if back_to:
        ui.link("← Back", back_to).classes("text-sm")
    with ui.row().classes("w-full items-center justify-between mt-2 mb-6"):
        with ui.column().classes("gap-0"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("rocket_launch", size="30").classes("text-accent")
                ui.label(SITE_NAME).classes("text-3xl font-black tracking-tight text-white")
            if title != SITE_NAME:
                ui.label(title).classes("text-sm mt-1")
    ui.label(_update_status()).classes("text-xs mt-[-16px] mb-4")


def _footer() -> None:
    with ui.row().classes("w-full justify-center mt-12 mb-4"):
        ui.label(f"{SITE_NAME} v{__version__} · made for Hack Club Nest").classes(
            "text-xs text-gray-600")


def build_event_cards(container, events: list[dict], detail_fn=None) -> None:
    """Render a responsive grid of event cards.

    ``detail_fn(ev, index)`` is called when a card is clicked; when None the
    cards are not clickable.
    """
    container.clear()
    container.style(
        "display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); "
        "gap:12px; align-items:start;"
    )
    if not events:
        with container:
            with ui.column().classes(
                    "w-full items-center justify-center gap-2 py-16").style(
                    "grid-column: 1 / -1;"):
                ui.icon("travel_explore", size="56").classes("text-gray-600")
                ui.label("Nothing scheduled in this window.").classes(
                    "text-lg text-gray-400 font-medium")
                ui.label("Try widening the date range or clearing the filters.").classes(
                    "text-sm text-gray-600")
        return

    with container:
        for idx, ev in enumerate(events):
            ev_time = ev.get("time")
            ts = ev_time.strftime("%b %d, %Y · %H:%M UTC") if ev_time else "Unknown time"
            countdown = ev.get("countdown") or "T-?"
            category = str(ev.get("category", "EVENT"))
            tag_bg, tag_fg = _cat_style(category)

            with ui.card().classes(
                    "w-full no-shadow rounded-xl transition hover:translate-y-[-2px] "
                    "cursor-pointer").style(
                    f"background:{PANEL_COLOR}; border:1px solid {BORDER_COLOR};") as card:
                with ui.row().classes("items-start justify-between w-full gap-3"):
                    with ui.column().classes("gap-1 flex-1 min-w-0"):
                        with ui.row().classes("items-center gap-2 flex-wrap"):
                            ui.label(ts).classes("text-xs text-gray-500")
                            ui.badge(category).props("outline").classes(
                                "text-[10px] tracking-wide").style(
                                f"background:{tag_bg}; color:{tag_fg};")
                        ui.label(str(ev.get("title", "Untitled"))).classes(
                            "text-lg font-semibold leading-snug text-gray-100")
                        ui.label(ev.get("info", "No details")).classes(
                            "text-sm text-gray-400 leading-relaxed")
                    ui.badge(countdown, text_color="black").props("color=primary").classes(
                        "shrink-0 px-3 py-1").style("background:#5898d4;")
                if detail_fn:
                    with ui.row().classes("w-full items-center justify-end mt-2"):
                        ui.label("Details →").classes("text-xs text-accent")
                if detail_fn:
                    card.on_click(lambda _ev=ev, _i=idx: detail_fn(_ev, _i))


def create_app(engine: SpaceEngine | None = None):
    """Build the NiceGUI home page and return it as the ``root`` callable.

    NiceGUI 3.x expects a ``root`` callable (a ``ui.page`` function) rather
    than global-scope UI, especially when the app is launched through a console
    -script entry point. Returning a callable keeps the route at ``/``
    registered so the auto-index fallback never has to re-run the entry script
    (which would crash).
    """
    global _ENGINE
    if engine is not None:
        _ENGINE = engine

    def root() -> None:
        _page_setup()
        _header()
        ui.label("Choose a track to explore.").classes(
            "text-lg text-gray-400 mb-8 text-center w-full")

        with ui.column().classes("w-full gap-4 max-w-2xl mx-auto"):
            for card in TRACK_CARDS:
                with ui.card().classes(
                        "w-full no-shadow rounded-xl transition hover:translate-y-[-2px] "
                        "cursor-pointer").style(
                        f"background:{PANEL_COLOR}; border:1px solid {BORDER_COLOR};") as c:
                    with ui.row().classes("items-center gap-4 w-full"):
                        ui.icon(card["icon"], size="36").classes("text-accent")
                        with ui.column().classes("gap-0"):
                            ui.label(card["label"]).classes(
                                "text-xl font-semibold text-gray-100")
                            ui.label(card["desc"]).classes("text-sm text-gray-400")
                    with ui.row().classes("w-full items-center justify-end mt-2"):
                        ui.label("Explore →").classes("text-xs text-accent")
                    c.on_click(
                        lambda _t=card["track"]: ui.navigate.to(f"/tracks/{_t}"))
        _footer()

    return root


def _track_info(track: str) -> dict | None:
    return next((c for c in TRACK_CARDS if c["track"] == track), None)


@ui.page("/tracks/{track}")
def track_page(track: str) -> None:
    _page_setup()

    info = _track_info(track)
    if info is None:
        _header(back_to="/")
        ui.label("Unknown track.").classes("text-gray-400")
        _footer()
        return

    _header(title=f"{info['label']} — timeline", back_to="/")
    ui.label(info["desc"]).classes("text-sm text-gray-500 mt-[-12px] mb-4")

    with ui.card().classes("w-full no-shadow rounded-xl").style(
            f"background:{PANEL_COLOR}; border:1px solid {BORDER_COLOR};"):
        with ui.row().classes("w-full items-end gap-4 flex-wrap"):
            name = ui.input("Name filter").props("outlined dense").classes("flex-1")
            after = ui.input("After (YYYY-MM-DD)").props("outlined dense").classes("flex-1")
            before = ui.input("Before (YYYY-MM-DD)").props("outlined dense").classes("flex-1")
            limit = ui.number("Limit", value=60, min=1, max=300).props(
                "outlined dense").classes("w-32 flex-1")

    status = ui.label("").classes("text-sm text-gray-400")
    results = ui.column().classes("w-full")

    def _parse(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    async def refresh() -> None:
        status.set_text("Fetching space data…").classes("text-accent")
        try:
            events = await asyncio.to_thread(
                _get_engine().get_events,
                track=track,
                after=_parse(after.value),
                before=_parse(before.value),
                name=name.value or None,
                limit=int(limit.value or 60),
            )
        except Exception as exc:
            status.set_text(f"Could not load events: {exc}").classes("text-red-400")
            return
        planned = sorted(events, key=lambda e: e.get("time") or datetime.min.replace(
            tzinfo=timezone.utc))
        count_label.set_text(f"Events ({len(planned)})")

        def goto(ev: dict, i: int) -> None:
            ui.navigate.to(f"/event/{track}/{_event_id(ev)}")

        build_event_cards(results, planned, detail_fn=goto)
        status.set_text(f"Showing {len(planned)} event(s).")

    auto_timer = ui.timer(30, refresh, active=False)

    async def _on_auto(e):
        auto_timer.active = bool(e.value)
        status.set_text(
            f"Auto-refresh {'on (every %ss)' % interval.value if e.value else 'off'}")
        if e.value:
            await refresh()

    def _on_interval():
        if auto_timer.active:
            auto_timer.interval = float(interval.value)

    with ui.row().classes("w-full items-center justify-between mt-1 flex-wrap gap-2"):
        count_label = ui.label("Events").classes("text-sm text-gray-400")
        with ui.row().classes("items-center gap-3"):
            interval = ui.select([15, 30, 60], value=30, label="every (s)").props(
                "outlined dense").classes("w-32").on_value_change(_on_interval)
            ui.switch("Auto-refresh").on_value_change(_on_auto)
            ui.button("Refresh", icon="refresh", on_click=refresh).props(
                "dense outline no-caps").classes("text-accent")

    ui.timer(0.6, refresh, once=True)

    _groq_card()
    _footer()


def _groq_card() -> None:
    from core.groq_chat import groq_chat

    with ui.card().classes("w-full no-shadow rounded-xl mt-4").style(
            f"background:{PANEL_COLOR}; border:1px solid {BORDER_COLOR};"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("psychology", size="22").classes("text-accent")
            ui.label("Ask Groq").classes("text-lg font-semibold text-gray-100")
        ui.label("Powered by Groq — ask about anything on this page.").classes(
            "text-xs text-gray-500")
        groq_input = ui.input("Your question").props("outlined dense").classes("w-full")
        groq_out = ui.label("").style("white-space: pre-wrap").classes(
            "text-sm text-gray-300 mt-1")

        async def _ask_groq() -> None:
            prompt = (groq_input.value or "").strip()
            if not prompt:
                groq_out.set_text("Type a question first.")
                return
            groq_out.set_text("Thinking…")
            answer = await asyncio.to_thread(groq_chat, prompt)
            groq_out.set_text(answer)

        ui.button("Ask", icon="send", on_click=_ask_groq).props(
            "dense outline no-caps").classes("text-accent mt-1")


@ui.page("/event/{track}/{eid}")
def event_page(track: str, eid: str) -> None:
    _page_setup()

    info = _track_info(track)
    if info is None:
        _header(back_to="/")
        ui.label("Unknown track.").classes("text-gray-400")
        return

    _header(title=f"{info['label']} — event", back_to=f"/tracks/{track}")

    slot = ui.column().classes("w-full gap-2")
    with slot:
        with ui.row().classes("w-full items-center justify-center gap-3 py-16"):
            ui.spinner(size="lg").classes("text-accent")
            ui.label("Loading event…").classes("text-gray-500")

    async def _load() -> None:
        # Fetching a track runs NOAA/thespacedevs calls and Skyfield's planetary
        # search, which can take much longer than the 3s page-build timeout. So
        # the page shell renders instantly and the heavy work happens here.
        events = await asyncio.to_thread(_track_events, track)
        ids = [_event_id(e) for e in events]
        idx = ids.index(eid) if eid in ids else -1

        slot.clear()
        with slot:
            if idx < 0:
                with ui.column().classes("w-full items-center gap-2 py-16"):
                    ui.icon("search_off", size="56").classes("text-gray-600")
                    ui.label("Event not found.").classes(
                        "text-lg text-gray-400 font-medium")
                    ui.link("← Back to timeline", f"/tracks/{track}").classes("text-sm")
                return
            _render_event(events[idx])
            with ui.row().classes("w-full items-center justify-between mt-6 gap-3"):
                if idx > 0:
                    ui.button("← Previous", icon="navigate_before",
                              on_click=lambda: ui.navigate.to(
                                  f"/event/{track}/{ids[idx - 1]}")
                              ).props("dense outline no-caps").classes("text-accent")
                if idx < len(events) - 1:
                    ui.button("Next →", icon="navigate_next",
                              on_click=lambda: ui.navigate.to(
                                  f"/event/{track}/{ids[idx + 1]}")
                              ).props("dense outline no-caps").classes("text-accent")

    ui.timer(0.1, _load, once=True)
    _footer()


def _render_event(ev: dict) -> None:
    ev_time = ev.get("time")
    ts = ev_time.strftime("%A, %B %d, %Y · %H:%M UTC") if ev_time else "Unknown time"
    countdown = ev.get("countdown") or "T-?"
    category = str(ev.get("category", "EVENT"))
    tag_bg, tag_fg = _cat_style(category)

    ui.label(str(ev.get("title", "Untitled"))).classes(
        "text-3xl font-bold text-gray-100 leading-tight mb-3")
    with ui.row().classes("items-center gap-2 flex-wrap mb-4"):
        ui.label(ts).classes("text-sm text-gray-500")
        ui.badge(category).props("outline").classes("text-[10px] tracking-wide").style(
            f"background:{tag_bg}; color:{tag_fg};")
        ui.badge(countdown, text_color="black").props("color=primary").classes(
            "px-3 py-1").style("background:#5898d4;")

    with ui.card().classes("w-full no-shadow rounded-xl").style(
            f"background:{PANEL_COLOR}; border:1px solid {BORDER_COLOR};"):
        ui.label("Details").classes("text-sm font-semibold text-gray-300 mb-2")
        ui.label(ev.get("info", "No details")).style("white-space: pre-wrap").classes(
            "text-sm text-gray-400 leading-relaxed")


def _start_bots() -> None:
    """Launch the chat bots in background threads.

    The web server owns the main thread; the Slack/Discord bots each run their
    own blocking loop in a daemon thread. Tokens are read from the environment,
    so a bot simply doesn't start if its credentials are absent — the server
    keeps serving the web app either way.
    """
    if os.environ.get("SLACK_BOT_TOK") and os.environ.get("SLACK_APP_TOK"):
        from core.slack_bot import SlackBot

        def _run_slack():
            try:
                SlackBot().run()
            except Exception:
                import traceback
                traceback.print_exc()

        threading.Thread(target=_run_slack, daemon=True).start()
    if os.environ.get("DISCORD_BOT_TOK"):
        from core.discord_bot import DiscordBot

        def _run_discord():
            try:
                DiscordBot().run()
            except Exception:
                import traceback
                traceback.print_exc()

        threading.Thread(target=_run_discord, daemon=True).start()


def serve() -> None:
    """Run the web app and the chat bots together on one server.

    Binds NiceGUI to ``0.0.0.0:$PORT`` (Hack Club Nest / HF Spaces) and starts
    any configured chat bots in the background. This is the entry point used by
    the repo-root ``app.py`` and the ``spacer-serve`` script.
    """
    _start_bots()

    ui.run(
        create_app(),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        show=False,
        title=SITE_NAME,
    )


def main() -> None:
    ui.run(
        create_app(),
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=False,
        show=False,
        title=SITE_NAME,
    )


if __name__ == "__main__":
    main()