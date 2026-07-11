import requests
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from typing import Tuple, Any, Optional

disable_warnings(category=InsecureRequestWarning)

class APIClient:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Spacer/1.0',
            'Accept': 'application/json'
        }

    def get(self, url: str, params: Optional[dict] = None, timeout: int = 12) -> Tuple[Optional[Any], Optional[str]]:
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=timeout, verify=False)
            if response.status_code != 200:
                return None, f"HTTP Error {response.status_code}: {response.text[:80]}"
            return response.json(), None
        except requests.exceptions.Timeout:
            return None, "Status: Request timed out."
        except requests.exceptions.RequestException as e:
            return None, f"Status: Context failed -> {str(e)}"

    def post(self, url: str, json_data: dict, timeout: int = 10) -> Tuple[bool, Optional[str]]:
        try:
            response = requests.post(url, json=json_data, timeout=timeout, verify=False)
            if response.status_code in [200, 204]:
                return True, None
            return False, f"HTTP Error {response.status_code}"
        except Exception as e:
            return False, str(e)
