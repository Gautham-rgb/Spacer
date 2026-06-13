from typing import List, Dict, Any
from .base import BaseEvent
from ..core.config import NOAA_WEATHER_URL
from ..core.utils import normalize_datetime

class SpaceWeatherEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="Weather")

    def fetch_timeline_data(self) -> List[Dict[str, Any]]:
        events = []
        
        # Past Weather
        past_url = f"{NOAA_WEATHER_URL}/products/noaa-space-weather-scale.json"
        past_data, _ = self.api_client.get(past_url)
        if isinstance(past_data, list):
            for item in past_data[:5]:
                events.append({
                    "time": normalize_datetime(item.get("time_tag", "")),
                    "category": "NOAA_PAST",
                    "title": f"Activity: {item.get('scale_id')}",
                    "info": f"Level: {item.get('level')} | {item.get('name')}"
                })

        # Forecast Weather
        forecast_url = f"{NOAA_WEATHER_URL}/json/forecasts/3-day-forecast.json"
        forecast_data, _ = self.api_client.get(forecast_url)
        if isinstance(forecast_data, list):
            for item in forecast_data:
                events.append({
                    "time": normalize_datetime(item.get("time_tag", "")),
                    "category": "NOAA_FORECAST",
                    "title": f"Forecast K-Index: {item.get('kp_index')}",
                    "info": f"Observed/Predicted at {item.get('time_tag')}"
                })
        
        return events
