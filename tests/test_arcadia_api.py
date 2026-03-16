from types import SimpleNamespace

import pytest
import requests

from tariff_fetch.arcadia.api import ArcadiaSignalAPI, ArcadiaSignalAPIAuth


def test_request_raises_http_error_with_arcadia_message():
    response = requests.Response()
    response.status_code = 403
    response.url = "https://api.genability.com/rest/public/tariffs"
    response.request = requests.Request("GET", response.url).prepare()
    response._content = b"""{
      "status": "error",
      "count": 1,
      "type": "Error",
      "results": [
        {
          "code": "tariffLimit",
          "message": "Unique tariff (MTIDs) limit reached. Please contact sales (arcsales@arcadia.com) for more information.",
          "objectName": "OrgUsage",
          "propertyName": "tariffLimit"
        }
      ],
      "pageCount": 25,
      "pageStart": 0
    }"""
    response.encoding = "utf-8"

    session = SimpleNamespace(get=lambda *args, **kwargs: response)
    api = ArcadiaSignalAPI(auth=ArcadiaSignalAPIAuth("id", "key"), session=session)  # type: ignore[arg-type]

    with pytest.raises(requests.HTTPError, match="Unique tariff \\(MTIDs\\) limit reached") as exc_info:
        api._request("tariffs")

    assert exc_info.value.response is response


def test_request_preserves_default_http_error_when_arcadia_message_missing():
    response = requests.Response()
    response.status_code = 403
    response.url = "https://api.genability.com/rest/public/tariffs"
    response.request = requests.Request("GET", response.url).prepare()
    response._content = b'{"status":"error","results":[{"code":"tariffLimit"}]}'
    response.encoding = "utf-8"

    session = SimpleNamespace(get=lambda *args, **kwargs: response)
    api = ArcadiaSignalAPI(auth=ArcadiaSignalAPIAuth("id", "key"), session=session)  # type: ignore[arg-type]

    with pytest.raises(requests.HTTPError, match="403 Client Error"):
        api._request("tariffs")
