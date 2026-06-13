from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..core.api_client import APIClient
from ..core.utils import normalize_datetime

class BaseEvent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.api_client = APIClient()

    @abstractmethod
    def fetch_timeline_data(self) -> List[Dict[str, Any]]:
        pass

    def safe_extract(self, data_dict: dict, keys_path: list, fallback: str = "N/A"):
        if not isinstance(data_dict, dict):
            return fallback
        current_level = data_dict
        for key in keys_path:
            if isinstance(current_level, dict) and key in current_level and current_level[key] is not None:
                current_level = current_level[key]
            else:
                return fallback
        return current_level
