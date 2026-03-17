import json
from pathlib import Path

import pytest
import requests
import typer

from tariff_fetch import cli_arcadia_urdb as cli


def test_cli_arcadia_urdb_fail_fast_passes_non_interactive(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ARCADIA_APP_ID", "id")
    monkeypatch.setenv("ARCADIA_APP_KEY", "key")
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())

    captured: dict[str, object] = {}

    def fake_build_urdb(api, scenario, *, interactive_errors: bool):
        captured["interactive_errors"] = interactive_errors
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    cli.main(123, 2025, output=tmp_path / "out.json", fail_fast=True)

    assert captured["interactive_errors"] is False


def test_cli_arcadia_urdb_json_errors_include_http_message(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("ARCADIA_APP_ID", "id")
    monkeypatch.setenv("ARCADIA_APP_KEY", "key")
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())

    response = requests.Response()
    response.status_code = 403
    response.url = "https://api.genability.com/rest/public/tariffs"
    response.request = requests.Request("GET", response.url).prepare()
    exc = requests.HTTPError("Unique tariff (MTIDs) limit reached.", response=response, request=response.request)

    def fake_build_urdb(api, scenario, *, interactive_errors: bool):
        raise exc

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    with pytest.raises(typer.Exit) as exc_info:
        cli.main(123, 2025, output=tmp_path / "out.json", json_errors=True)

    assert exc_info.value.exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "error": "Unique tariff (MTIDs) limit reached.",
        "exit_code": 1,
        "provider": "arcadia",
        "status_code": 403,
    }
