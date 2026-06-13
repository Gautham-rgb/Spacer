import itertools
from typing import List, Dict, Any
from skyfield.api import load
from skyfield.searchlib import find_minima, find_maxima
from .base import BaseEvent

class AstronomyEvent(BaseEvent):
    def __init__(self):
        super().__init__(name="Astronomy")
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        self.targets = [
            'mercury', 
            'venus', 
            'mars', 
            'jupiter barycenter', 
            'saturn barycenter'
        ]

    def fetch_timeline_data(self, year: int = 2026) -> List[Dict[str, Any]]:
        events = []
        t0 = self.ts.utc(year, 1, 1)
        t1 = self.ts.utc(year, 12, 31)

        for p1, p2 in itertools.combinations(self.targets, 2):
            def separation_function(t):
                obs1 = self.earth.at(t).observe(self.eph[p1]).apparent()
                obs2 = self.earth.at(t).observe(self.eph[p2]).apparent()
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
