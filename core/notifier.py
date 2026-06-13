import os
from plyer import notification
from .api_client import APIClient
from .config import DEFAULT_CACHE_FILE

class Notifier:
    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE):
        self.cache_file = cache_file
        self.api_client = APIClient()

    def should_notify(self, event_title: str) -> bool:
        if not os.path.exists(self.cache_file):
            open(self.cache_file, 'w').close()
        
        with open(self.cache_file, 'r') as f:
            notified = f.read().splitlines()
        
        if event_title in notified:
            return False
            
        with open(self.cache_file, 'a') as f:
            f.write(event_title + '
')
        return True

    def send_desktop_notification(self, title: str, message: str):
        try:
            notification.notify(
                title=f"Spacer Alert: {title}",
                message=message,
                timeout=10
            )
            print(f"-> Notification sent for {title}")
        except Exception as e:
            print(f"-> Notification error: {e}")

    def send_webhook(self, url: str, event: dict):
        from .utils import calculate_countdown
        
        ev_time = event.get('time')
        time_str = ev_time.strftime('%H:%M UTC') if ev_time else "Unknown Time"
        countdown_str = calculate_countdown(ev_time)

        payload = {
            "content": f"""**{event.get('category', 'Space Event')} in {countdown_str}**
            **Event:** {event.get('title', 'Untitled')}
            **Info:** {event.get('info', 'No details')}
            **Time:** {time_str}"""
        }
        success, err = self.api_client.post(url, payload)
        if success:
            print(f"-> Webhook sent successfully for {event.get('title')}")
        else:
            print(f"-> Webhook failed: {err}")
