import os

# The one canonical list of data tracks. CLI, desktop GUI, web home cards, and
# bot help text all derive their choices from here so they can't drift apart.
TRACKS = ["all", "space_weather", "space_events", "probe_launch", "probe_events"]
TRACK_NAMES = TRACKS[1:]  # the real trackers, without the "all" wildcard

NASA_API_KEY = os.environ.get("API_KEY", "DEMO_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or None
# Default to a model available on Groq's free tier (llama-3.1-8b-instant and
# llama-3.3-70b-versatile were deprecated 2026-08-16). Override with GROQ_MODEL.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
NASA_BASE_URL = "https://lldev.thespacedevs.com/2.2.0"
NOAA_WEATHER_URL = "https://services.swpc.noaa.gov"
DEFAULT_CACHE_FILE = "notified_events.txt"
