import argparse
from rich.console import Console
from datetime import datetime, timezone
from engine import SpaceEngine

def parse_cli_date(date_str: str) -> datetime:
    try: return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError: raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")

def main():
    parser = argparse.ArgumentParser(description="Spacer CLI Router")
    parser.add_argument("track", choices=["all", "space_weather", "space_events", "probe_launch", "probe_events"], help="Event category to track")
    parser.add_argument("action", choices=["list", "notify"])
    parser.add_argument("--after", type=parse_cli_date, help="YYYY-MM-DD")
    parser.add_argument("--before", type=parse_cli_date, help="YYYY-MM-DD")
    parser.add_argument("--name", type=str, help="Filter by name")
    parser.add_argument("--webhook", type=str, help="Optional webhook URL")
    
    args = parser.parse_args()
    
    engine = SpaceEngine()
    
    console = Console()
    with console.status("[bold green]Fetching space data..."):
        engine.run(
            track=args.track,
            action=args.action,
            after=args.after,
            before=args.before,
            name=args.name,
            webhook_url=args.webhook
        )

if __name__ == "__main__":
    main()
