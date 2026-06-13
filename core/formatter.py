from rich.console import Console

class TimelineFormatter:
    def __init__(self):
        self.console = Console()

    def render_cli(self, events: list):
        if not events:
            print("No events found for this timeframe.")
            return

        events.sort(key=lambda x: x.get('time'))
        print(f"
▲ LIVE PRODUCTION EVENT GRAPH")
        print("=" * 70)
        for ev in events:
            from .utils import calculate_countdown
            category_tag = str(ev.get('category', 'EVENT')).upper()
            ev_time = ev.get('time')
            countdown = calculate_countdown(ev_time)
            print(f"[{ev_time.strftime('%Y-%m-%d %H:%M UTC')}] ({countdown})")
            print(f" └── [{category_tag}] {ev.get('title', 'Untitled')}")
            print(f"      {ev.get('info', 'No details.')[:60]}...
")
        print("=" * 70)

    def render_markdown(self, events: list):
        if not events:
            return "No events found for this timeframe."

        events.sort(key=lambda x: x.get('time'))
        from .utils import calculate_countdown
        
        headers, dividers, timestamps, countdowns, summaries = [], [], [], [], []
        for ev in events:
            category_tag = str(ev.get('category', 'EVENT')).upper()
            headers.append(f"**{category_tag}**")
            dividers.append(" :--- ")
            ev_time = ev.get('time')
            timestamps.append(f"`{ev_time.strftime('%m/%d %H:%M')}`")
            countdowns.append(f"*{calculate_countdown(ev_time)}*")
            summaries.append(f"**{ev.get('title')}**<br>{ev.get('info')[:45]}")

        return (
            f"| " + " | ".join(headers) + " |
" + f"|" + "|".join(dividers) + "|
" +
            f"| " + " | ".join(timestamps) + " |
" + f"| " + " | ".join(countdowns) + " |
" +
            f"| " + " | ".join(summaries) + " |"
        )
