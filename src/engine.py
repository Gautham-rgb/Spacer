from datetime import datetime, timezone, timedelta
from typing import Any

from core.notifier import Notifier
from core.formatter import TimelineFormatter
from core.cache import EventCache
from core.utils import calculate_countdown
from events.events import AstronomyEvent, ProbeEvent, SpaceWeatherEvent


class SpaceEngine:
    """Headless core of Spacer.

    Gathers events from the configured trackers, filters them, and optionally
    notifies/renders. :meth:`get_events` is the single source of truth that the
    CLI, chat bots, desktop GUI, and web app all consume — no front-end
    re-implements fetching.
    """

    def __init__(self, cache: EventCache | None = None):
        self.notifier = Notifier()
        self.formatter = TimelineFormatter()
        self.cache = cache or EventCache()
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

    def get_events(self, track: str = "all", after: datetime | None = None,
                   before: datetime | None = None, name: str | None = None,
                   limit: int | None = None,
                   use_cache: bool = True) -> list[dict[str, Any]]:
        """Gather + filter only. No rendering, no notifications.

        This is the single source of truth the CLI, GUI, and web front-ends
        should all consume. Results are cached (TTL) unless ``use_cache`` is
        False, so the UIs don't hammer NOAA + thespacedevs on every refresh.
        A human-readable ``countdown`` is stamped onto every event.
        """
        cache_key = EventCache.make_key(track, name, limit)
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                filtered = cached
            else:
                filtered = self._gather(track, name, limit)
                self.cache.set(cache_key, filtered)
        else:
            filtered = self._gather(track, name, limit)

        if after:
            filtered = [e for e in filtered if e.get('time') and e['time'] >= after]
        if before:
            filtered = [e for e in filtered if e.get('time') and e['time'] <= before]

        for ev in filtered:
            ev["countdown"] = calculate_countdown(ev.get('time')) #type: ignore
        return filtered

    def _gather(self, track: str, name: str | None,
                limit: int | None) -> list[dict[str, Any]]:
        targets = self.get_trackers(track)
        pool: list[dict[str, Any]] = []
        for t in targets:
            pool.extend(t.fetch_timeline_data())
        filtered = pool
        if name:
            filtered = [e for e in filtered if name.lower() in e.get('title', '').lower()]
        if limit:
            filtered = filtered[:limit]
        return filtered

    def run(self, track: str, action: str, after: datetime | None = None,
            before: datetime | None = None, name: str | None = None,
            limit: int | None = None, webhook_url: str | None = None):
        """Fetch + filter, then either notify or render the timeline."""
        filtered = self.get_events(track, after, before, name, limit)

        # Action: Notify
        if action == "notify":
            now = datetime.now(timezone.utc)
            for ev in filtered:
                ev_time = ev.get('time', now)
                if now < ev_time <= (now + timedelta(hours=1)):
                    if self.notifier.should_notify(ev['title']):
                        self.notifier.send_desktop_notification(
                            ev['title'],
                            f"""{ev.get('info', 'No details')}
                            Time: {ev_time.strftime('%H:%M UTC')}"""
                        )
                        if webhook_url:
                            self.notifier.send_webhook(webhook_url, ev)

        # Action: List (Timeline)
        else:
            if webhook_url:
                markdown = self.formatter.render_markdown(filtered)
                self.notifier.send_generic_webhook(webhook_url, f"### Live Timeline:\n{markdown}")

            self.formatter.render_cli(filtered)
