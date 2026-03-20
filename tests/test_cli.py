import json
from datetime import date
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

    def fake_process_genability(*, utility: Utility, output_folder: Path, effective_on: date | None = None):
        captured["utility"] = utility
        captured["output_folder"] = output_folder
        captured["effective_on"] = effective_on

    monkeypatch.setattr(cli, "process_genability", fake_process_genability)

    result = runner.invoke(
        cli.app,
        ["raw", "--state", "ny", "--provider", "genability", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
        "effective_on": None,
    }


def test_raw_command_uses_prompted_provider_when_flag_is_missing(monkeypatch, tmp_path: Path):
    utility = Utility(eia_id=111, name="Prompted Utility")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "prompt_provider", lambda: Provider.OPENEI)
    monkeypatch.setattr(cli, "prompt_utility", lambda state: utility)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_process_openei(selected_utility: Utility, output_folder: Path, effective_on: date | None = None):
        captured["utility"] = selected_utility
        captured["output_folder"] = output_folder
        captured["effective_on"] = effective_on

    monkeypatch.setattr(cli, "process_openei", fake_process_openei)

    result = runner.invoke(
        cli.app,
        ["raw", "--state", "ny", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
        "effective_on": None,
    }


def test_default_command_passes_effective_date_to_provider(monkeypatch, tmp_path: Path):
    utility = Utility(eia_id=303, name="Default Utility")
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "prompt_provider", lambda: Provider.GENABILITY)
    monkeypatch.setattr(cli, "prompt_utility", lambda state: utility)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_process_genability(*, utility: Utility, output_folder: Path, effective_on: date | None = None):
        captured["utility"] = utility
        captured["output_folder"] = output_folder
        captured["effective_on"] = effective_on

    monkeypatch.setattr(cli, "process_genability", fake_process_genability)

    result = runner.invoke(
        cli.app,
        ["--state", "ny", "--output-folder", str(tmp_path), "--effective-date", "2025-06-01"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
        "effective_on": date(2025, 6, 1),
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


def test_gas_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "process_rateacuity_gas",
        lambda output_folder, state: captured.update(
            {
                "output_folder": output_folder,
                "state": state,
            }
        ),
    )

    result = runner.invoke(
        cli.app,
        ["gas", "--state", "tx", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "output_folder": tmp_path,
        "state": "tx",
    }


def test_gas_urdb_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli,
        "process_rateacuity_gas_urdb",
        lambda output_folder, state, year: captured.update(
            {
                "output_folder": output_folder,
                "state": state,
                "year": year,
            }
        ),
    )

    result = runner.invoke(
        cli.app,
        ["gas", "urdb", "--state", "tx", "--output-folder", str(tmp_path), "--year", "2025"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "output_folder": tmp_path,
        "state": "tx",
        "year": 2025,
    }


def test_ni_arcadia_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "arcadia.json"
    captured: dict[str, object] = {}
    fake_results = [{"master_tariff_id": 123, "tariff_name": "Example Tariff"}]

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    class FakeTypeAdapter:
        def __init__(self, _type):
            pass

        def dump_json(self, value, *, indent: int):
            assert indent == 2
            return json.dumps(value, indent=indent).encode()

    class FakeTariffsAPI:
        def iter_pages(self, **kwargs):
            captured["iter_pages_kwargs"] = kwargs
            return iter(fake_results)

    class FakeArcadiaSignalAPI:
        def __init__(self):
            self.tariffs = FakeTariffsAPI()

    monkeypatch.setattr(cli, "ArcadiaSignalAPI", FakeArcadiaSignalAPI)
    monkeypatch.setattr(cli, "TypeAdapter", FakeTypeAdapter)

    result = runner.invoke(
        cli.app,
        ["ni", "arcadia", "123", "2025-06-01", "--output", str(output_path)],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["iter_pages_kwargs"] == {
        "fields": "ext",
        "master_tariff_id": 123,
        "effective_on": date(2025, 6, 1),
        "populate_properties": True,
        "populate_rates": True,
    }
    assert output_path.exists()
    assert json.loads(output_path.read_text()) == fake_results
