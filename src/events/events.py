import itertools
import os
from typing import List, Dict, Any
from datetime import datetime, timezone
from skyfield.api import load
from skyfield.searchlib import find_minima, find_maxima
from .base import BaseEvent
from core.config import NASA_BASE_URL
from core.config import NOAA_WEATHER_URL
from core.utils import normalize_datetime
from core.enricher import EventEnricher


def _locate_bsp() -> str:
    """Find the bundled JPL ephemeris, regardless of the current directory.

    Checks a few candidate locations (repo root, package dir, then the raw
    name so Skyfield can use its own cache/download as a last resort).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "de421.bsp"),
        os.path.join(here, "de421.bsp"),
        "de421.bsp",
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return "de421.bsp"


class SpaceWeatherEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="Weather")

    def fetch_timeline_data(self) -> List[Dict[str, Any]]:
        events = []

        # Past Weather
        past_url = f"{NOAA_WEATHER_URL}/products/noaa-space-weather-scale.json"
        past_data, _ = self.api_client.get(past_url)
        # NOAA returns either a list or an object that nests the list under a key.
        if isinstance(past_data, list):
            past_items = past_data
        elif isinstance(past_data, dict):
            past_items = past_data.get("reports") or past_data.get("errors") or []
        else:
            past_items = []
        for item in past_items[:5]:
            if isinstance(item, dict):
                events.append({
                    "time": normalize_datetime(item.get("time_tag", "")),
                    "category": "NOAA_PAST",
                    "title": f"Activity: {item.get('scale_id')}",
                    "info": f"Level: {item.get('level')} | {item.get('name')}"
                })

        # Forecast Weather
        forecast_url = f"{NOAA_WEATHER_URL}/json/forecasts/3-day-forecast.json"
        forecast_data, _ = self.api_client.get(forecast_url)
        if isinstance(forecast_data, dict):
            forecast_items = forecast_data.get("forecasts") or forecast_data.get("forecast") or [forecast_data]
        elif isinstance(forecast_data, list):
            forecast_items = forecast_data
        else:
            forecast_items = []
        for item in forecast_items:
            if isinstance(item, dict):
                events.append({
                    "time": normalize_datetime(item.get("time_tag", "")),
                    "category": "NOAA_FORECAST",
                    "title": f"Forecast K-Index: {item.get('kp_index')}",
                    "info": f"Observed/Predicted at {item.get('time_tag')}"
                })

        return events
    
class ProbeEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="Probe")
        self.enricher = EventEnricher()

    def fetch_timeline_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        url = f"{NASA_BASE_URL}/launch/"
        data, err = self.api_client.get(url, params={"limit": limit, "ordering": "net"})
        if not data or "results" not in data:
            return []
            
        events = []
        for item in data["results"]:
            name = item.get("name", "Unknown Mission")
            mission = item.get("mission") or {}
            desc_text = mission.get("description")
            
            if not desc_text or len(desc_text) < 20:
                wiki_info = self.enricher.get_wiki_summary(name)
                ai_summary = self.enricher.get_ai_summary(
                    f"Summarize this mission in a few concise sentences: {wiki_info}"
                )
                desc_text = ai_summary if ai_summary else wiki_info
            
            events.append({
                "time": normalize_datetime(item.get("window_start", "")),
                "category": self.name,
                "title": name,
                "info": desc_text[:100] + "..."
            })
        return events


class AstronomyEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="Astronomy")
        self.ts = load.timescale()
        self.eph = load(_locate_bsp())
        self.earth = self.eph['earth']
        self.targets = [
            'mercury', 
            'venus', 
            'mars', 
            'jupiter barycenter', 
            'saturn barycenter'
        ]

    def fetch_timeline_data(self, year: int | None = None) -> List[Dict[str, Any]]:
        if year is None:
            year = datetime.now(timezone.utc).year
        events = []
        t0 = self.ts.utc(year, 1, 1)
        t1 = self.ts.utc(year, 12, 31)

        for p1, p2 in itertools.combinations(self.targets, 2):
            def separation_function(t):
                obs1 = self.earth.at(t).observe(self.eph[p1]).apparent() #type: ignore
                obs2 = self.earth.at(t).observe(self.eph[p2]).apparent() #type: ignore
                return obs1.separation_from(obs2).degrees

            separation_function.step_days = 1.0

            self._process_search(
                find_minima(t0, t1, separation_function),
                f"{p1.capitalize()}-{p2.capitalize()} Conjunction",
                "Closest approach: {val:.2f}°",
                lambda val: val < 3.0,
                events
            )

            self._process_search(
                find_maxima(t0, t1, separation_function),
                f"{p1.capitalize()}-{p2.capitalize()} 180° Alignment",
                "Angle: {val:.2f}°",
                lambda val: val > 175.0,
                events
            )
        return events

    def _process_search(self, search_results, title, info_fmt, condition, event_list):
        times, values = search_results
        for t, val in zip(times, values):
            if condition(val):
                event_list.append({
                    'time': t.utc_datetime(),
                    'title': title,
                    'info': info_fmt.format(val=val),
                    'category': "PLANETARY"
                })
