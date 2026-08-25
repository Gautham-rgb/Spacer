import argparse
import sys
import os
from rich.console import Console
from datetime import datetime, timezone

# Add the `src` directory to sys.path so top-level imports (engine, core,
# events, CLI_bot) resolve when running from a checkout without installation.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import SpaceEngine
from version import __version__


def parse_cli_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")


def build_parser():
    parser = argparse.ArgumentParser(description="Spacer CLI Router")
    parser.add_argument("track", nargs="?", default="all",
                        choices=["all", "space_weather", "space_events", "probe_launch", "probe_events"],
                        help="Event category to track (default: all)")
    parser.add_argument("action", nargs="?", default="list",
                        choices=["list", "notify"], help="Action to perform (default: list)")
    parser.add_argument("--after", type=parse_cli_date, help="YYYY-MM-DD")
    parser.add_argument("--before", type=parse_cli_date, help="YYYY-MM-DD")
    parser.add_argument("--name", type=str, help="Filter by name")
    parser.add_argument("-l", "--limit", type=int, help="Limit the number of events returned")
    parser.add_argument("--webhook", type=str, help="Optional webhook URL")
    parser.add_argument("--slack", action="store_true",
                        help="Run the interactive Slack bot (Socket Mode)")
    parser.add_argument("--discord", action="store_true",
                        help="Run the interactive Discord bot")
    parser.add_argument("--version", "-V", action="version",
                        version=f"spacer {__version__}")
    parser.add_argument("--check-update", action="store_true",
                        help="Check PyPI for a newer release and exit")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    from core.env import load_env
    load_env()

    if args.check_update:
        from core.updates import check_for_update
        print(check_for_update())
        return

    if args.slack:
        from core.slack_bot import SlackBot
        SlackBot().run()
        return

    if args.discord:
        from core.discord_bot import DiscordBot
        DiscordBot().run()
        return

    engine = SpaceEngine()

    console = Console()
    console.print(f"[bold cyan]Spacer[/bold cyan] [dim](v{__version__})[/dim]")
    with console.status("[bold green]Fetching space data..."):
        engine.run(
            track=args.track,
            action=args.action,
            after=args.after,
            before=args.before,
            name=args.name,
            limit=args.limit,
            webhook_url=args.webhook
        )


if __name__ == "__main__":
    main()
