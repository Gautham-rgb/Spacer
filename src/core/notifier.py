import os
from core.api_client import APIClient
from core.config import DEFAULT_CACHE_FILE

class Notifier:
    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE):
        self.cache_file = cache_file
        self.api_client = APIClient()
        self._notification = None  # plyer is imported lazily (headless-safe)

    def should_notify(self, event_title: str) -> bool:
        if not os.path.exists(self.cache_file):
            open(self.cache_file, 'w').close()
        
        with open(self.cache_file, 'r') as f:
            notified = f.read().splitlines()
        
        if event_title in notified:
            return False
            
        with open(self.cache_file, 'a') as f:
            f.write(event_title + '\n')
        return True

    def send_desktop_notification(self, title: str, message: str):
        # plyer needs a display; on a headless server this is a no-op.
        if self._notification is None:
            try:
                from plyer import notification
                self._notification = notification
            except Exception:
                self._notification = False
        if not self._notification:
            return
        try:
            self._notification.notify(
                title=f"Spacer Alert: {title}",
                message=message,
                timeout=10
            )
            print(f"-> Notification sent for {title}")
        except Exception as e:
            print(f"-> Notification error: {e}")

    def send_generic_webhook(self, url: str, message: str):
        # Slack uses 'text', Discord/others typically use 'content'
        key = "text" if "slack.com" in url.lower() else "content"
        payload = {key: message}
        
        success, err = self.api_client.post(url, payload)
        if success:
            print(f"-> Webhook sent successfully")
        else:
            print(f"-> Webhook failed: {err}")
        return success, err

    def send_webhook(self, url: str, event: dict):
        from core.utils import calculate_countdown
        
        ev_time = event.get('time')
        time_str = ev_time.strftime('%H:%M UTC') if ev_time else "Unknown Time"
        countdown_str = calculate_countdown(ev_time) #type: ignore

        message = f"**{event.get('category', 'Space Event')} in {countdown_str}**\n" \
                  f"**Event:** {event.get('title', 'Untitled')}\n" \
                  f"**Info:** {event.get('info', 'No details')}\n" \
                  f"**Time:** {time_str}"
        
        return self.send_generic_webhook(url, message)
