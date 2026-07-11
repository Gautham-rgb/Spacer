from datetime import datetime, timezone
import requests

def normalize_datetime(date_string: str) -> datetime:
    if not date_string or not isinstance(date_string, str) or date_string == "N/A":
        return datetime.now(timezone.utc)
    try:
        clean_str = date_string.replace('Z', '+00:00').strip()
        if "T" in clean_str:
            if "." in clean_str:
                base_part, nano_part = clean_str.split(".")
                tz_offset = ""
                if "+" in nano_part:
                    nano_part, tz_offset = nano_part.split("+", 1)
                    tz_offset = "+" + tz_offset
                clean_str = f"{base_part}.{nano_part[:6]}{tz_offset}"
            return datetime.fromisoformat(clean_str)
        return datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def calculate_countdown(target_time: datetime) -> str:
    now = datetime.now(timezone.utc)
    if not isinstance(target_time, datetime):
        return "T-unknown"
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)
        
    time_delta = target_time - now
    total_seconds = time_delta.total_seconds()
    
    prefix = "T-" if total_seconds >= 0 else ""
    suffix = " ago" if total_seconds < 0 else ""
    
    abs_seconds = abs(int(total_seconds))
    days, remainder = divmod(abs_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0: return f"{prefix}{days}d {hours}h{suffix}"
    if hours > 0: return f"{prefix}{hours}h {minutes}m{suffix}"
    return f"{prefix}{minutes}m{suffix}"
