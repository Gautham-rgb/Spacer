"""Spacer CLI: management + events.

A proper argparse interface split into command groups::

    spacer events list  [TRACK] [--after --before --name --limit --format cli|md|json]
    spacer events show   [TRACK] SELECTOR [--after --before --name]
    spacer tracks
    spacer config
    spacer health
    spacer notify [TRACK] [--name --limit --webhook]
    spacer cache clear | stats
    spacer update
    spacer -V | --version

The ``--slack`` / ``--discord`` flags from the original `router` entry point
are preserved because docker-compose launches the bots that way.
"""

from __future__ import annotations

import os
import sys

# Make top-level packages (engine, core, events, ...) importable when running
# straight from a checkout, before anything tries to import them.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import time
from datetime import datetime, timedelta, timezone

from core.env import load_env
from core.config import TRACKS, NOAA_WEATHER_URL, NASA_BASE_URL
from version import __version__


def parse_cli_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")


def _event_time(ev: dict) -> str:
    ev_time = ev.get("time")
    return ev_time.strftime("%Y-%m-%d %H:%M UTC") if isinstance(ev_time, datetime) else "Unknown"


def _window(after: datetime | None, before: datetime | None) -> tuple[datetime, datetime | None]:
    """Default to the last day -> next two weeks when no dates are given."""
    if after is None and before is None:
        now = datetime.now(timezone.utc)
        return now - timedelta(days=1), now + timedelta(days=14)
    return after, before


def _to_json(ev: dict) -> dict:
    return {
        key: (value.isoformat() if isinstance(value, datetime) else value)
        for key, value in ev.items()
    }


def list_events(args) -> int:
    from engine import SpaceEngine

    engine = SpaceEngine()
    after, before = _window(args.after, args.before)
    events = engine.get_events(
        track=args.track,
        after=after,
        before=before,
        name=args.name,
        limit=args.limit,
    )
    if args.format == "json":
        print(json.dumps([_to_json(e) for e in events], indent=2))
    elif args.format == "md":
        print(engine.formatter.render_markdown(events))
    else:
        engine.formatter.render_cli(events)
    return 0


def show_event(args) -> int:
    from engine import SpaceEngine

    engine = SpaceEngine()
    after, before = _window(args.after, args.before)
    events = engine.get_events(
        track=args.track,
        after=after,
        before=before,
        name=args.name,
        limit=args.limit,
    )
    if not events:
        print("No events found for the current filters.")
        return 0

    if args.selector.isdigit():
        idx = int(args.selector) - 1
        if not 0 <= idx < len(events):
            print(f"Index {args.selector} out of range (1..{len(events)}).")
            return 2
        match = events[idx]
    else:
        needle = args.selector.lower()
        matches = [e for e in events if needle in (e.get("title") or "").lower()]
        if not matches:
            print(f"No event matches '{args.selector}'.")
            return 1
        if len(matches) > 1:
            print(f"{len(matches)} events match; pass an index (1..{len(events)}) to disambiguate:")
            for i, e in enumerate(matches, 1):
                print(f"  {i}. {e.get('title')} @ {_event_time(e)}")
            return 2
        match = matches[0]

    print(f"Title:    {match.get('title', 'Untitled')}")
    print(f"Category: {str(match.get('category', 'EVENT')).upper()}")
    print(f"Time:     {_event_time(match)}")
    print(f"Countdown: {match.get('countdown') or 'T-unknown'}")
    print(f"Details:  {match.get('info') or 'No details.'}")
    return 0


def show_tracks() -> int:
    from core.pyproject import track_cards

    for card in track_cards():
        print(f"- {card['track']:<16} {card['label']}: {card['desc']}")
    return 0


def show_config() -> int:
    import os

    from core.pyproject import track_cards

    cards = track_cards()
    print(f"spacer {__version__}")
    print(f"tracks:      {', '.join(c['track'] for c in cards)}")
    print(f"cache file:  .spacer_cache.json (ttl 1800s)")
    print(f"groq model:  {os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')}")
    for name, label in (("GROQ_API_KEY", "groq api key"),
                        ("DISCORD_BOT_TOK", "discord token"),
                        ("SLACK_BOT_TOK", "slack bot token"),
                        ("SLACK_APP_TOK", "slack app token"),
                        ("API_KEY", "nasa api key")):
        print(f"{label}: {'set' if os.environ.get(name) else 'unset'}")
    return 0


def run_health() -> int:
    from core.api_client import APIClient

    api = APIClient()
    checks = [
        ("noaa k-index", f"{NOAA_WEATHER_URL}/products/noaa-planetary-k-index-forecast.json", None),
        ("noaa flare", f"{NOAA_WEATHER_URL}/json/goes/primary/xray-flares-latest.json", None),
        ("thespacedevs", f"{NASA_BASE_URL}/launch/", {"limit": 1, "ordering": "net"}),
    ]
    failed = 0
    for name, url, params in checks:
        t0 = time.perf_counter()
        _, err = api.get(url, params=params, timeout=10)
        ms = (time.perf_counter() - t0) * 1000
        if err:
            failed += 1
            print(f"FAIL  {name:<14} {err}")
        else:
            print(f"OK    {name:<14} {ms:.0f}ms")

    try:
        from skyfield.api import load
        from events.events import _locate_bsp

        t0 = time.perf_counter()
        load(_locate_bsp())
        ms = (time.perf_counter() - t0) * 1000
        print(f"OK    {'skyfield':<14} {ms:.0f}ms (local ephemeris)")
    except Exception as exc:  # noqa: BLE001 - any init failure = unhealthy
        failed += 1
        print(f"FAIL  {'skyfield':<14} {exc}")

    print("health:", "all checks passed" if not failed else f"{failed} check(s) failed")
    return 0 if not failed else 1


def run_notify(args) -> int:
    from engine import SpaceEngine

    engine = SpaceEngine()
    now = datetime.now(timezone.utc)
    engine.run(
        track=args.track,
        action="notify",
        after=now,
        before=now + timedelta(hours=1),
        name=args.name,
        limit=args.limit,
        webhook_url=args.webhook,
    )
    print("Checked for events in the next hour.")
    return 0


def run_cache(args) -> int:
    from core.cache import EventCache

    cache = EventCache()
    if args.cache_command == "clear":
        cache.clear()
        print(f"cache cleared ({cache.file})")
        return 0

    stats = cache.stats()
    print(f"cache file: {stats['file']} (ttl {cache.ttl}s)")
    if not stats["entries"]:
        print("no cached queries")
        return 0
    for key, info in stats["entries"].items():
        print(f"{key:<28} {info['events']:>4} events   {info['age_s']}s old")
    return 0


def run_update() -> int:
    from core.updates import check_for_update

    print(check_for_update(notify_error=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spacer", description="Spacer: space-weather, "
                                   "astronomy, and launch events.")
    parser.add_argument("-V", "--version", action="version", version=f"spacer {__version__}")
    parser.add_argument("--slack", dest="bot_slack", action="store_true",
                        help="Run the interactive Slack bot (Socket Mode).")
    parser.add_argument("--discord", dest="bot_discord", action="store_true",
                        help="Run the interactive Discord bot.")

    sub = parser.add_subparsers(dest="command")

    p_events = sub.add_parser("events", help="List or inspect events.")
    esub = p_events.add_subparsers(dest="events_command", required=True)

    p_list = esub.add_parser("list", help="List a timeline of events.")
    p_list.add_argument("track", nargs="?", default="all", choices=TRACKS)
    p_list.add_argument("--after", type=parse_cli_date)
    p_list.add_argument("--before", type=parse_cli_date)
    p_list.add_argument("--name", help="Substring filter on the event title.")
    p_list.add_argument("-l", "--limit", type=int)
    p_list.add_argument("-F", "--format", choices=["cli", "md", "json"], default="cli")

    p_show = esub.add_parser("show", help="Show full details for one event.")
    p_show.add_argument("track", nargs="?", default="all", choices=TRACKS)
    p_show.add_argument("selector", help="1-based index (in the listed set) or title substring.")
    p_show.add_argument("--after", type=parse_cli_date)
    p_show.add_argument("--before", type=parse_cli_date)
    p_show.add_argument("--name", help="Substring filter on the event title.")
    p_show.add_argument("-l", "--limit", type=int)

    sub.add_parser("tracks", help="List the configured tracks.")

    sub.add_parser("config", help="Show effective configuration.")

    sub.add_parser("health", help="Check every upstream API.")

    p_notify = sub.add_parser("notify", help="Check for events in the next hour.")
    p_notify.add_argument("track", nargs="?", default="all", choices=TRACKS)
    p_notify.add_argument("--name")
    p_notify.add_argument("-l", "--limit", type=int)
    p_notify.add_argument("--webhook", help="Optional webhook URL.")

    p_cache = sub.add_parser("cache", help="Cache management.")
    csub = p_cache.add_subparsers(dest="cache_command", required=True)
    csub.add_parser("clear", help="Delete the cache file.")
    csub.add_parser("stats", help="Show cached queries and their age.")

    sub.add_parser("update", help="Check PyPI for a newer release.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    load_env()

    if args.bot_slack:
        from core.slack_bot import SlackBot
        return SlackBot().run()

    if args.bot_discord:
        from core.discord_bot import DiscordBot
        return DiscordBot().run()

    if args.command == "events":
        if args.events_command == "list":
            return list_events(args)
        return show_event(args)
    if args.command == "tracks":
        return show_tracks()
    if args.command == "config":
        return show_config()
    if args.command == "health":
        return run_health()
    if args.command == "notify":
        return run_notify(args)
    if args.command == "cache":
        return run_cache(args)
    if args.command == "update":
        return run_update()

    from types import SimpleNamespace
    return list_events(SimpleNamespace(
        track="all", after=None, before=None, name=None, limit=None, format="cli"))


if __name__ == "__main__":
    sys.exit(main())