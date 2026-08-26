import os

NASA_API_KEY = os.environ.get("API_KEY", "DEMO_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or None
# Default to a model available on Groq's free tier. Override with GROQ_MODEL.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
NASA_BASE_URL = "https://lldev.thespacedevs.com/2.2.0"
NOAA_WEATHER_URL = "https://services.swpc.noaa.gov"
DEFAULT_CACHE_FILE = "notified_events.txt"
