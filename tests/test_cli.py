import json
from pathlib import Path

from typer.testing import CliRunner

from tariff_fetch import cli
from tariff_fetch._cli import console
from tariff_fetch._cli.types import Provider, Utility

runner = CliRunner()


def test_raw_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    utility = Utility(eia_id=101, name="Test Utility")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "prompt_utility", lambda state: utility)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_process_genability(*, utility: Utility, output_folder: Path):
        captured["utility"] = utility
        captured["output_folder"] = output_folder

    monkeypatch.setattr(cli, "process_genability", fake_process_genability)

    result = runner.invoke(
        cli.app,
        ["raw", "--state", "ny", "--provider", "genability", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
    }


def test_raw_command_uses_prompted_provider_when_flag_is_missing(monkeypatch, tmp_path: Path):
    utility = Utility(eia_id=111, name="Prompted Utility")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "prompt_provider", lambda: Provider.OPENEI)
    monkeypatch.setattr(cli, "prompt_utility", lambda state: utility)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_process_openei(selected_utility: Utility, output_folder: Path):
        captured["utility"] = selected_utility
        captured["output_folder"] = output_folder

    monkeypatch.setattr(cli, "process_openei", fake_process_openei)

    result = runner.invoke(
        cli.app,
        ["raw", "--state", "ny", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
    }


def test_urdb_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    utility = Utility(eia_id=202, name="URDB Utility")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "prompt_utility", lambda state: utility)
    monkeypatch.setattr(cli, "prompt_year", lambda: 2024)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_process_genability_urdb(*, utility: Utility, output_folder: Path, year: int, interactive_errors: bool):
        captured["utility"] = utility
        captured["output_folder"] = output_folder
        captured["year"] = year
        captured["interactive_errors"] = interactive_errors

    monkeypatch.setattr(cli, "process_genability_urdb", fake_process_genability_urdb)

    result = runner.invoke(
        cli.app,
        ["urdb", "--state", "wa", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
        "year": 2024,
        "interactive_errors": True,
    }


def test_urdb_ni_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_build_urdb(api, scenario, *, interactive_errors: bool):
        captured["api"] = api
        captured["scenario"] = scenario
        captured["interactive_errors"] = interactive_errors
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    result = runner.invoke(
        cli.app,
        ["urdb", "ni", "123", "2025", "--output", str(output_path), "--fail-fast"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["interactive_errors"] is False
    assert output_path.exists()
    assert json.loads(output_path.read_text()) == {
        "label": "UTIL",
        "utility": "Utility",
        "name": "Tariff",
        "country": "USA",
    }
