from rich.console import Console

class TimelineFormatter:
    def __init__(self):
        self.console = Console()

    def render_cli(self, events: list):
        if not events:
            print("No events found for this timeframe.")
            return

        events.sort(key=lambda x: x.get('time'))
        print(f"\n▲ LIVE PRODUCTION EVENT GRAPH")
        print("=" * 70)
        for ev in events:
            from core.utils import calculate_countdown
            category_tag = str(ev.get('category', 'EVENT')).upper()
            ev_time = ev.get('time')
            countdown = calculate_countdown(ev_time)
            print(f"[{ev_time.strftime('%Y-%m-%d %H:%M UTC')}] ({countdown})")
            print(f" └── [{category_tag}] {ev.get('title', 'Untitled')}")
            print(f"      {ev.get('info', 'No details.')[:60]}...\n")
        print("=" * 70)

    def render_markdown(self, events: list):
        if not events:
            return "No events found for this timeframe."

        events.sort(key=lambda x: x.get('time'))
        from core.utils import calculate_countdown
        
        lines = []
        for ev in events:
            category_tag = str(ev.get('category', 'EVENT')).upper()
            ev_time = ev.get('time')
            timestamp = ev_time.strftime('%m/%d %H:%M UTC') if ev_time else "Unknown"
            countdown = calculate_countdown(ev_time)
            
            line = (f"• **[{category_tag}]** {ev.get('title', 'Untitled')}\n"
                    f"  `{timestamp}` ({countdown})\n"
                    f"  _{ev.get('info', 'No details')[:100]}...")
            lines.append(line)

        return "\n\n".join(lines)
