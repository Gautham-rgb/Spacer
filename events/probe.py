from typing import List, Dict, Any
from .base import BaseEvent
from ..core.config import NASA_BASE_URL
from ..core.utils import normalize_datetime
from ..core.enricher import EventEnricher

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
                desc_text = self.enricher.get_ai_summary(
                    f"Summarize this mission in a few concise sentences: {wiki_info}"
                )
            
            events.append({
                "time": normalize_datetime(item.get("window_start", "")),
                "category": self.name,
                "title": name,
                "info": desc_text[:100] + "..."
            })
        return events
