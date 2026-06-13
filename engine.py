from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from .core.notifier import Notifier
from .core.formatter import TimelineFormatter
from .events.astronomy import AstronomyEvent
from .events.probe import ProbeEvent
from .events.weather import SpaceWeatherEvent

class SpaceEngine:
    def __init__(self):
        self.notifier = Notifier()
        self.formatter = TimelineFormatter()
        self.trackers = {
            "space_weather": SpaceWeatherEvent(),
            "space_events": AstronomyEvent(),
            "probe_launch": ProbeEvent(),
            "probe_events": ProbeEvent(),
        }

    def get_trackers(self, track: str):
        if track == "all":
            return list(self.trackers.values())
        return [self.trackers[track]] if track in self.trackers else []

    def run(self, track: str, action: str, after: Optional[datetime] = None, 
             before: Optional[datetime] = None, name: Optional[str] = None, 
             webhook_url: Optional[str] = None):
        
        targets = self.get_trackers(track)
        pool = []
        
        # 1. Gather
        for t in targets:
            pool.extend(t.fetch_timeline_data())

        # 2. Filter
        filtered = pool
        if name:
            filtered = [e for e in filtered if name.lower() in e['title'].lower()]
        if after:
            filtered = [e for e in filtered if e['time'] >= after]
        if before:
            filtered = [e for e in filtered if e['time'] <= before]

        # 3. Action: Notify
        if action == "notify":
            now = datetime.now(timezone.utc)
            for ev in filtered:
                # Notify if within the next hour
                if now < ev.get('time', now) <= (now + timedelta(hours=1)):
                    if self.notifier.should_notify(ev['title']):
                        self.notifier.send_desktop_notification(
                            ev['title'], 
                            f"{ev.get('info', 'No details')}
Time: {ev['time'].strftime('%H:%M UTC')}"
                        )
                        if webhook_url:
                            self.notifier.send_webhook(webhook_url, ev)
        
        # 4. Action: List (Timeline)
        else:
            if webhook_url:
                markdown = self.formatter.render_markdown(filtered)
                # Use notifier's api client to send the markdown timeline
                self.notifier.api_client.post(webhook_url, {"content": f"### Live Timeline:
{markdown}"})
            
            self.formatter.render_cli(filtered)
