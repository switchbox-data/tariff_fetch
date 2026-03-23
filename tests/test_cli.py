import json
from datetime import date
from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from tariff_fetch import cli
from tariff_fetch._cli import console
from tariff_fetch._cli.types import Provider, Utility
from tariff_fetch.urdb.arcadia.scenario import Scenario

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


def test_raw_command_no_input_fails_before_prompt(tmp_path: Path):
    result = runner.invoke(
        cli.app,
        ["raw", "--no-input", "--output-folder", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "Prompt requires interactive input but --no-input was set: Select state" in result.output


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

    def fake_process_genability_urdb(
        *,
        utility: Utility,
        output_folder: Path,
        year: int,
        interactive_errors: bool,
        properties: dict[str, object] | None = None,
    ):
        captured["utility"] = utility
        captured["output_folder"] = output_folder
        captured["year"] = year
        captured["interactive_errors"] = interactive_errors
        captured["properties"] = properties

    monkeypatch.setattr(cli, "process_genability_urdb", fake_process_genability_urdb)

    result = runner.invoke(
        cli.app,
        ["urdb", "--state", "wa", "--output-folder", str(tmp_path), "--property", "territoryId=1"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "utility": utility,
        "output_folder": tmp_path,
        "year": 2024,
        "interactive_errors": True,
        "properties": {"territoryId": "1"},
    }


def test_urdb_ni_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_build_urdb(api, scenario: Scenario, *, interactive_errors: bool):
        captured["api"] = api
        captured["scenario"] = scenario
        captured["interactive_errors"] = interactive_errors
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    result = runner.invoke(
        cli.app,
        [
            "urdb",
            "ni",
            "123",
            "2025",
            "--output",
            str(output_path),
            "--fail-fast",
            "--property",
            "territoryId=1",
            "--property",
            "territoryId=2",
            "--property",
            "netMetering=true",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["interactive_errors"] is False
    assert cast(Scenario, captured["scenario"]).properties == {"territoryId": ["1", "2"], "netMetering": "true"}
    assert output_path.exists()
    assert json.loads(output_path.read_text()) == {
        "label": "UTIL",
        "utility": "Utility",
        "name": "Tariff",
        "country": "USA",
    }


def test_urdb_ni_command_supports_charge_class_shortcuts(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_build_urdb(api, scenario: Scenario, *, interactive_errors: bool):
        captured["scenario"] = scenario
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    result = runner.invoke(
        cli.app,
        [
            "urdb",
            "ni",
            "123",
            "2025",
            "--output",
            str(output_path),
            "--cc",
            "Stn",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert cast(Scenario, captured["scenario"]).charge_classes == {"SUPPLY", "TAX", "NET_EXCESS"}


def test_urdb_ni_command_supports_dash_cc_alias(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_build_urdb(api, scenario: Scenario, *, interactive_errors: bool):
        captured["scenario"] = scenario
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    result = runner.invoke(
        cli.app,
        [
            "urdb",
            "ni",
            "123",
            "2025",
            "--output",
            str(output_path),
            "-cc",
            "St",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert cast(Scenario, captured["scenario"]).charge_classes == {"SUPPLY", "TAX"}


def test_urdb_ni_command_merges_charge_class_flags(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"
    captured: dict[str, object] = {}

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_build_urdb(api, scenario: Scenario, *, interactive_errors: bool):
        captured["scenario"] = scenario
        return {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"}

    monkeypatch.setattr(cli, "build_urdb", fake_build_urdb)

    result = runner.invoke(
        cli.app,
        [
            "urdb",
            "ni",
            "123",
            "2025",
            "--output",
            str(output_path),
            "--charge-class",
            "SUPPLY",
            "--cc",
            "Dn",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert cast(Scenario, captured["scenario"]).charge_classes == {"SUPPLY", "DISTRIBUTION", "NET_EXCESS"}


def test_urdb_ni_command_rejects_invalid_charge_class_shortcuts(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    result = runner.invoke(
        cli.app,
        [
            "urdb",
            "ni",
            "123",
            "2025",
            "--output",
            str(output_path),
            "--cc",
            "Sz",
        ],
    )

    assert result.exit_code == 1


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


def test_gas_ni_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "gas_rateacuity.json"
    captured: dict[str, object] = {}
    fake_results = [{"schedule": "Firm Gas Service", "sections": []}]

    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_fetch_rateacuity_gas_tariffs(*, state: str, utility_query: str, tariff_queries: list[str]):
        captured["state"] = state
        captured["utility_query"] = utility_query
        captured["tariff_queries"] = tariff_queries
        return "Consolidated Edison Gas", fake_results

    monkeypatch.setattr(cli, "fetch_rateacuity_gas_tariffs", fake_fetch_rateacuity_gas_tariffs)

    result = runner.invoke(
        cli.app,
        [
            "gas",
            "ni",
            "ny",
            "con ed gas",
            "--tariff",
            "firm gas service",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "state": "ny",
        "utility_query": "con ed gas",
        "tariff_queries": ["firm gas service"],
    }
    assert json.loads(output_path.read_text()) == fake_results


def test_gas_urdb_ni_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "gas_rateacuity_urdb.json"
    captured: dict[str, object] = {}
    fake_results = [{"label": "ceg", "utility": "Consolidated Edison Gas", "name": "Firm Gas Service"}]

    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_fetch_rateacuity_gas_urdb_rates(
        *,
        state: str,
        utility_query: str,
        tariff_queries: list[str],
        year: int,
        apply_percentages: bool,
        label: str | None,
        sector: str,
        servicetype: str,
    ):
        captured["state"] = state
        captured["utility_query"] = utility_query
        captured["tariff_queries"] = tariff_queries
        captured["year"] = year
        captured["apply_percentages"] = apply_percentages
        captured["label"] = label
        captured["sector"] = sector
        captured["servicetype"] = servicetype
        return "Consolidated Edison Gas", fake_results

    monkeypatch.setattr(cli, "fetch_rateacuity_gas_urdb_rates", fake_fetch_rateacuity_gas_urdb_rates)

    result = runner.invoke(
        cli.app,
        [
            "gas",
            "urdb",
            "ni",
            "ny",
            "con ed gas",
            "--year",
            "2025",
            "--tariff",
            "firm gas service",
            "--label",
            "ceg",
            "--sector",
            "Commercial",
            "--servicetype",
            "Delivery",
            "--apply-percentages",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "state": "ny",
        "utility_query": "con ed gas",
        "tariff_queries": ["firm gas service"],
        "year": 2025,
        "apply_percentages": True,
        "label": "ceg",
        "sector": "Commercial",
        "servicetype": "Delivery",
    }
    assert json.loads(output_path.read_text()) == {"items": fake_results}


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


def test_show_properties_command_runs_end_to_end(monkeypatch):
    captured: dict[str, object] = {}
    fake_results = [{"properties": [{"key_name": "territoryId"}]}]

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_fetch_arcadia_tariffs(*, master_tariff_id: int, effective_on: date, populate_rates: bool):
        captured["master_tariff_id"] = master_tariff_id
        captured["effective_on"] = effective_on
        captured["populate_rates"] = populate_rates
        return fake_results

    def fake_print_arcadia_properties(results):
        captured["results"] = results

    monkeypatch.setattr(cli, "_fetch_arcadia_tariffs", fake_fetch_arcadia_tariffs)
    monkeypatch.setattr(cli, "_print_arcadia_properties", fake_print_arcadia_properties)

    result = runner.invoke(
        cli.app,
        ["show-properties", "123", "2025-06-01"],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "master_tariff_id": 123,
        "effective_on": date(2025, 6, 1),
        "populate_rates": True,
        "results": fake_results,
    }


def test_ni_openei_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "openei.json"
    captured: dict[str, object] = {}
    fake_results = [{"name": "Residential Tariff", "label": "abc"}]

    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_fetch_openei_tariffs(*, eia_id: int, sector: str, detail: str, effective_on: date):
        captured["eia_id"] = eia_id
        captured["sector"] = sector
        captured["detail"] = detail
        captured["effective_on"] = effective_on
        return fake_results

    monkeypatch.setattr(cli, "_fetch_openei_tariffs", fake_fetch_openei_tariffs)

    result = runner.invoke(
        cli.app,
        [
            "ni",
            "openei",
            "123",
            "Residential",
            "2025-06-01",
            "--detail",
            "minimal",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "eia_id": 123,
        "sector": "Residential",
        "detail": "minimal",
        "effective_on": date(2025, 6, 1),
    }
    assert json.loads(output_path.read_text()) == {"items": fake_results}


def test_ni_rateacuity_command_runs_end_to_end(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "rateacuity.json"
    captured: dict[str, object] = {}
    fake_results = [{"schedule": "Residential Service", "sections": []}]

    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)

    def fake_fetch_rateacuity_tariffs(*, state: str, utility_query: str, tariff_queries: list[str]):
        captured["state"] = state
        captured["utility_query"] = utility_query
        captured["tariff_queries"] = tariff_queries
        return "Consolidated Edison Company of New York", fake_results

    monkeypatch.setattr(cli, "fetch_rateacuity_tariffs", fake_fetch_rateacuity_tariffs)

    result = runner.invoke(
        cli.app,
        [
            "ni",
            "rateacuity",
            "fuzzy",
            "ny",
            "con ed",
            "--tariff",
            "residential service",
            "--tariff",
            "time of use",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "state": "ny",
        "utility_query": "con ed",
        "tariff_queries": ["residential service", "time of use"],
    }
    assert json.loads(output_path.read_text()) == fake_results


def test_ni_rateacuity_command_supports_eia_id_lookup(monkeypatch, tmp_path: Path):
    output_path = tmp_path / "rateacuity.json"
    captured: dict[str, object] = {}
    fake_results = [{"schedule": "Residential Service", "sections": []}]

    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cli,
        "_get_utility_by_eia_id",
        lambda eia_id: cli._UtilityLookup(eia_id=eia_id, name="Consolidated Edison", state="NY"),
    )

    def fake_fetch_rateacuity_tariffs(*, state: str, utility_query: str, tariff_queries: list[str]):
        captured["state"] = state
        captured["utility_query"] = utility_query
        captured["tariff_queries"] = tariff_queries
        return "Consolidated Edison Company of New York", fake_results

    monkeypatch.setattr(cli, "fetch_rateacuity_tariffs", fake_fetch_rateacuity_tariffs)

    result = runner.invoke(
        cli.app,
        [
            "ni",
            "rateacuity",
            "eia-id",
            "123",
            "--tariff",
            "residential service",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured == {
        "state": "ny",
        "utility_query": "Consolidated Edison",
        "tariff_queries": ["residential service"],
    }
    assert json.loads(output_path.read_text()) == fake_results


def test_collect_arcadia_property_rows_merges_choices_across_tariffs():
    tariffs = [
        {
            "properties": [
                {
                    "key_name": "chargeClass",
                    "display_name": "Charge class",
                    "data_type": "CHOICE",
                    "description": "Handled separately",
                    "choices": [
                        {"value": "SUPPLY", "display_value": "Supply", "data_value": "SUPPLY"},
                    ],
                },
                {
                    "key_name": "territoryId",
                    "display_name": "Territory",
                    "data_type": "CHOICE",
                    "description": "Select the service territory",
                },
            ]
        },
        {
            "properties": [
                {
                    "key_name": "territoryId",
                    "display_name": "Territory",
                    "data_type": "CHOICE",
                    "description": "Select the service territory",
                    "choices": [
                        {"value": "1", "display_value": "Primary Territory", "data_value": "1"},
                        {"value": "2", "display_value": "Secondary Territory", "data_value": "2"},
                    ],
                }
            ]
        },
    ]

    assert cli._collect_arcadia_property_rows(tariffs) == {
        "territoryId": (
            "Territory",
            "CHOICE",
            "Select the service territory",
            "Primary Territory=1, Secondary Territory=2",
        )
    }
