from datetime import date
from pathlib import Path
from types import SimpleNamespace

from tariff_fetch._cli import genability
from tariff_fetch._cli.types import Utility


def test_process_genability_prints_replay_command(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(genability, "load_dotenv", lambda: None)
    monkeypatch.setattr(genability, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(genability, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(
        genability, "q", SimpleNamespace(confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: True))
    )
    monkeypatch.setattr(genability, "_find_utility_lse_id", lambda api, utility: 1)
    monkeypatch.setattr(genability, "_select_customer_classes", lambda: ["RESIDENTIAL"])
    monkeypatch.setattr(genability, "_select_tariff_types", lambda: ["DEFAULT"])
    monkeypatch.setattr(
        genability,
        "_select_tariffs",
        lambda api, lse_id, customer_classes, tariff_types, effective_on: [("Tariff", 123)],
    )
    monkeypatch.setattr(
        genability,
        "_fetch_tariffs",
        lambda api, tariffs, effective_on: [{"master_tariff_id": 123, "tariff_name": "Tariff"}],
    )
    monkeypatch.setattr(
        genability, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(genability.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    genability.process_genability(
        utility=Utility(eia_id=1, name="Utility"),
        output_folder=tmp_path,
        effective_on=date(2025, 6, 1),
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch ni arcadia ")]
    assert replay_lines == ["tariff-fetch ni arcadia 123 2025-06-01"]


def test_process_genability_prints_multiple_replay_commands(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(genability, "load_dotenv", lambda: None)
    monkeypatch.setattr(genability, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(genability, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(
        genability, "q", SimpleNamespace(confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: True))
    )
    monkeypatch.setattr(genability, "_find_utility_lse_id", lambda api, utility: 1)
    monkeypatch.setattr(genability, "_select_customer_classes", lambda: ["RESIDENTIAL"])
    monkeypatch.setattr(genability, "_select_tariff_types", lambda: ["DEFAULT"])
    monkeypatch.setattr(
        genability,
        "_select_tariffs",
        lambda api, lse_id, customer_classes, tariff_types, effective_on: [("Tariff A", 123), ("Tariff B", 456)],
    )
    monkeypatch.setattr(
        genability,
        "_fetch_tariffs",
        lambda api, tariffs, effective_on: [
            {"master_tariff_id": 123, "tariff_name": "Tariff A"},
            {"master_tariff_id": 456, "tariff_name": "Tariff B"},
        ],
    )
    monkeypatch.setattr(
        genability, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(genability.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    genability.process_genability(
        utility=Utility(eia_id=1, name="Utility"),
        output_folder=tmp_path,
        effective_on=date(2025, 6, 1),
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch ni arcadia ")]
    assert replay_lines == ["tariff-fetch ni arcadia 123 2025-06-01", "tariff-fetch ni arcadia 456 2025-06-01"]


def test_process_genability_stops_when_replay_proceed_is_declined(monkeypatch, tmp_path: Path):
    printed: list[str] = []
    fetched: dict[str, object] = {}

    monkeypatch.setattr(genability, "load_dotenv", lambda: None)
    monkeypatch.setattr(genability, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(genability, "ArcadiaSignalAPI", lambda: object())
    monkeypatch.setattr(
        genability, "q", SimpleNamespace(confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: False))
    )
    monkeypatch.setattr(genability, "_find_utility_lse_id", lambda api, utility: 1)
    monkeypatch.setattr(genability, "_select_customer_classes", lambda: ["RESIDENTIAL"])
    monkeypatch.setattr(genability, "_select_tariff_types", lambda: ["DEFAULT"])
    monkeypatch.setattr(
        genability,
        "_select_tariffs",
        lambda api, lse_id, customer_classes, tariff_types, effective_on: [("Tariff", 123)],
    )
    monkeypatch.setattr(
        genability,
        "_fetch_tariffs",
        lambda api, tariffs, effective_on: fetched.update({"called": True}),
    )
    monkeypatch.setattr(
        genability, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(genability.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    genability.process_genability(
        utility=Utility(eia_id=1, name="Utility"),
        output_folder=tmp_path,
        effective_on=date(2025, 6, 1),
    )

    assert fetched == {}
