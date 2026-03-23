from datetime import date
from pathlib import Path
from types import SimpleNamespace

from tariff_fetch._cli import openei
from tariff_fetch._cli.types import Utility


def test_process_openei_prints_replay_command(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(openei, "load_dotenv", lambda: None)
    monkeypatch.setattr(openei, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(openei, "_prompt_sector", lambda: "Residential")
    monkeypatch.setattr(openei, "_prompt_detail_level", lambda: "minimal")
    monkeypatch.setattr(
        openei,
        "_get_tariffs",
        lambda eia_id, sector, detail, effective_on: [
            {"name": "Tariff A", "label": "abc"},
            {"name": "Tariff B", "label": "def"},
        ],
    )
    monkeypatch.setattr(openei, "_prompt_tariffs", lambda tariffs: [tariffs[0]])
    monkeypatch.setattr(openei, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json")
    monkeypatch.setattr(openei.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    openei.process_openei(
        utility=Utility(eia_id=123, name="Utility"),
        output_folder=tmp_path,
        effective_on=date(2025, 6, 1),
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch ni openei ")]
    assert replay_lines == ["tariff-fetch ni openei 123 Residential 2025-06-01 --detail minimal --label abc"]


def test_process_openei_prints_multiple_replay_commands(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(openei, "load_dotenv", lambda: None)
    monkeypatch.setattr(openei, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(openei, "_prompt_sector", lambda: "Residential")
    monkeypatch.setattr(openei, "_prompt_detail_level", lambda: "minimal")
    monkeypatch.setattr(
        openei,
        "_get_tariffs",
        lambda eia_id, sector, detail, effective_on: [
            {"name": "Tariff A", "label": "abc"},
            {"name": "Tariff B", "label": "def"},
        ],
    )
    monkeypatch.setattr(openei, "_prompt_tariffs", lambda tariffs: tariffs)
    monkeypatch.setattr(openei, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json")
    monkeypatch.setattr(openei.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))

    openei.process_openei(
        utility=Utility(eia_id=123, name="Utility"),
        output_folder=tmp_path,
        effective_on=date(2025, 6, 1),
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch ni openei ")]
    assert replay_lines == [
        "tariff-fetch ni openei 123 Residential 2025-06-01 --detail minimal --label abc",
        "tariff-fetch ni openei 123 Residential 2025-06-01 --detail minimal --label def",
    ]
