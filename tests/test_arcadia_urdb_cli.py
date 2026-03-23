from pathlib import Path
from types import SimpleNamespace

from tariff_fetch._cli import arcadia_urdb
from tariff_fetch._cli.types import Utility


def test_process_genability_prints_replay_command(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(arcadia_urdb, "load_dotenv", lambda: None)
    monkeypatch.setattr(arcadia_urdb, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(arcadia_urdb, "_find_utility_lse_id", lambda api, utility: 1)
    monkeypatch.setattr(arcadia_urdb, "_select_customer_classes", lambda: ["RESIDENTIAL"])
    monkeypatch.setattr(arcadia_urdb, "_select_tariff_types", lambda: ["DEFAULT"])
    monkeypatch.setattr(
        arcadia_urdb, "_select_tariffs", lambda api, lse_id, customer_classes, tariff_types, year: [("Tariff", 123)]
    )
    monkeypatch.setattr(
        arcadia_urdb,
        "_fetch_tariffs",
        lambda api, tariffs, year: [
            {
                "master_tariff_id": 123,
                "tariff_name": "Tariff",
                "properties": [
                    {"key_name": "territoryId", "display_name": "Territory"},
                    {"key_name": "netMetering", "display_name": "Net Metering"},
                ],
            }
        ],
    )
    monkeypatch.setattr(
        arcadia_urdb,
        "q",
        SimpleNamespace(confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: False)),
    )
    monkeypatch.setattr(arcadia_urdb, "prompt_charge_classes", lambda: {"SUPPLY", "TAX"})
    monkeypatch.setattr(arcadia_urdb, "_prompt_tariff_name", lambda default: default)
    monkeypatch.setattr(
        arcadia_urdb, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(arcadia_urdb.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    def fake_build_urdb(api, scenario, *, interactive_errors):
        scenario.properties["Territory"] = ["1", "2"]
        scenario.properties["netMetering"] = True
        return {"name": "Tariff"}

    monkeypatch.setattr(arcadia_urdb, "build_urdb", fake_build_urdb)

    arcadia_urdb.process_genability(
        utility=Utility(eia_id=1, name="Utility"),
        output_folder=tmp_path,
        year=2025,
        interactive_errors=True,
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch urdb ni ")]
    assert replay_lines == [
        "tariff-fetch urdb ni 123 2025 --no-apply-percentages -cc St --property netMetering=true --property territoryId=1 --property territoryId=2"
    ]


def test_process_genability_prints_multiple_replay_commands_without_default_charge_class_flag(
    monkeypatch, tmp_path: Path
):
    printed: list[str] = []

    monkeypatch.setattr(arcadia_urdb, "load_dotenv", lambda: None)
    monkeypatch.setattr(arcadia_urdb, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(arcadia_urdb, "_find_utility_lse_id", lambda api, utility: 1)
    monkeypatch.setattr(arcadia_urdb, "_select_customer_classes", lambda: ["RESIDENTIAL"])
    monkeypatch.setattr(arcadia_urdb, "_select_tariff_types", lambda: ["DEFAULT"])
    monkeypatch.setattr(
        arcadia_urdb,
        "_select_tariffs",
        lambda api, lse_id, customer_classes, tariff_types, year: [("Tariff A", 123), ("Tariff B", 456)],
    )
    monkeypatch.setattr(
        arcadia_urdb,
        "_fetch_tariffs",
        lambda api, tariffs, year: [
            {"master_tariff_id": 123, "tariff_name": "Tariff A", "properties": []},
            {"master_tariff_id": 456, "tariff_name": "Tariff B", "properties": []},
        ],
    )
    monkeypatch.setattr(
        arcadia_urdb,
        "q",
        SimpleNamespace(confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: True)),
    )
    monkeypatch.setattr(arcadia_urdb, "prompt_charge_classes", lambda: set(arcadia_urdb._ALL_CHARGE_CLASSES))
    monkeypatch.setattr(arcadia_urdb, "_prompt_tariff_name", lambda default: default)
    monkeypatch.setattr(
        arcadia_urdb, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(arcadia_urdb.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))
    monkeypatch.setattr(arcadia_urdb, "build_urdb", lambda api, scenario, *, interactive_errors: {"name": "Tariff"})

    arcadia_urdb.process_genability(
        utility=Utility(eia_id=1, name="Utility"),
        output_folder=tmp_path,
        year=2025,
        interactive_errors=True,
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch urdb ni ")]
    assert replay_lines == ["tariff-fetch urdb ni 123 2025", "tariff-fetch urdb ni 456 2025"]
