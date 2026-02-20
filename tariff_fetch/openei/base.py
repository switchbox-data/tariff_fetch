import datetime
from typing import Any
from urllib.parse import urljoin

import requests

BASE_URL = "https://api.openei.org"


def convert_params(input: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    return {k: _convert_param(v) for k, v in input.items()}  # pyright: ignore[reportAny]


def _convert_param(value: Any):  # pyright: ignore[reportAny, reportExplicitAny]
    if isinstance(value, datetime.datetime):
        return int(value.timestamp())
    return value  # pyright:ignore[reportAny]
    # return {True: "true", False: "false"}.get(value, value)


def api_request_json(path: str, api_key: str, **params) -> dict | list:  # pyright: ignore[reportMissingTypeArgument, reportUnknownParameterType, reportMissingParameterType]
    params_ = {"api_key": api_key, **convert_params(params)}  # pyright: ignore[reportUnknownArgumentType]
    url = urljoin(BASE_URL, path)
    response = requests.get(url, params=params_)
    response.raise_for_status()
    return response.json()  # pyright: ignore[reportAny]
