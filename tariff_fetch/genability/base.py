from typing import Any

import requests
from requests.models import HTTPBasicAuth

BASE_URL = "https://sandbox.api.genability.com/rest/public"


def api_request_json(url: str, auth: tuple[str, str], params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(url, params=params, auth=HTTPBasicAuth(*auth))
    response.raise_for_status()
    return response.json()
