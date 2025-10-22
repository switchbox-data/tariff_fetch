import os
from typing import Any

import requests
from dotenv import load_dotenv
from requests.models import HTTPBasicAuth

BASE_URL = "https://api.genability.com/rest/public"


def api_request_json(url: str, auth: tuple[str, str] | None = None, **params) -> dict[str, Any]:
    if auth is None:
        load_dotenv()
        app_id = os.getenv("ARCADIA_APP_ID")
        if app_id is None:
            raise ValueError("ARCADIA_APP_ID variable is not set. Either set it or use auth as a parameter.")
        app_key = os.getenv("ARCADIA_APP_KEY")
        if app_key is None:
            raise ValueError("ARCADIA_APP_KEY variable is not set. Either set it or use auth as a parameter.")
    else:
        app_id, app_key = auth
    response = requests.get(url, params=params, auth=HTTPBasicAuth(app_id, app_key))
    response.raise_for_status()
    return response.json()
