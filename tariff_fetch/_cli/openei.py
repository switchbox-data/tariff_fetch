import json
import os
import shlex
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv

from tariff_fetch import questionary_typed as q
from tariff_fetch.openei.utility_rates import UtilityRateSector, UtilityRatesResponseItem, iter_utility_rates

from . import console, prompt_filename
from .types import Utility


def _prompt_sector() -> UtilityRateSector:
    result = q.select(
        message="Select sector",
        choices=[
            "Residential",
            "Commercial",
            "Industrial",
            "Lighting",
        ],
    ).ask_or_exit()
    return cast(UtilityRateSector, result)


def _prompt_detail_level() -> Literal["full", "minimal"]:
    result = q.select(
        message="Select level of detail",
        choices=["full", "minimal"],
    ).ask_or_exit()
    return cast(Literal["full", "minimal"], result)


def _get_tariffs(
    eia_id: int, sector: UtilityRateSector, detail: Literal["full", "minimal"], effective_on: date | None = None
) -> list[UtilityRatesResponseItem]:
    api_key = os.getenv("OPENEI_API_KEY")
    if not api_key:
        raise ValueError("API Key is not set (via OPENEI_API_KEY variable)")
    with console.status("Fetching rates..."):
        iterator = iter_utility_rates(
            api_key,
            effective_on_date=datetime.combine(
                effective_on or datetime.now(UTC).date(), datetime.min.time(), tzinfo=UTC
            ),
            sector=sector,
            detail=detail,
            eia=eia_id,
        )
        return list(iterator)


def _prompt_tariffs(tariffs: list[UtilityRatesResponseItem]) -> list[UtilityRatesResponseItem]:
    result = q.checkbox(
        message="Select tariffs to include",
        choices=[q.Choice(title=tariff["name"], value=tariff, checked=True) for tariff in tariffs],
    ).ask()
    return result or []


def process_openei(utility: Utility, output_folder: Path, effective_on: date | None = None):
    _ = load_dotenv()
    if not os.getenv("OPENEI_API_KEY"):
        console.print("[b]OPENEI_API_KEY[/] environment variable is not set")
        console.print("Cannot use OpenEI API due to missing credentials")
        _ = console.input("Press enter to proceed...")
        return

    if not (sector := _prompt_sector()):
        return
    if not (detail_level := _prompt_detail_level()):
        return
    tariffs = _get_tariffs(utility.eia_id, sector, detail_level, effective_on)
    if not tariffs:
        console.print("[red]No tariffs found[/]")
        _ = console.input("Press enter to proceed...")
        return
    tariffs = _prompt_tariffs(tariffs)
    if not tariffs:
        console.print("[red]No tariffs selected[/]")
        _ = console.input("Press enter to proceed...")
        return

    suggested_filename = f"openei_{utility.name}_{sector}_{detail_level}"
    if not (filepath := prompt_filename(output_folder, suggested_filename, "json")):
        return

    filepath.parent.mkdir(exist_ok=True)
    wrapped_items = {"items": tariffs}
    _ = filepath.write_text(json.dumps(wrapped_items, indent=2))
    console.print(f"Wrote [blue]{len(tariffs)}[/] items to {filepath}")
    console.print("Replay with `tariff-fetch ni openei`:")
    for replay_command in _format_replay_commands(utility.eia_id, sector, detail_level, effective_on, tariffs):
        console.print(replay_command)


def _format_replay_commands(
    eia_id: int,
    sector: UtilityRateSector,
    detail: Literal["full", "minimal"],
    effective_on: date | None,
    tariffs: list[UtilityRatesResponseItem],
) -> list[str]:
    effective_date = (effective_on or datetime.now(UTC).date()).isoformat()
    return [
        shlex.join(
            [
                "tariff-fetch",
                "ni",
                "openei",
                str(eia_id),
                sector,
                effective_date,
                "--detail",
                detail,
                "--label",
                tariff["label"],
            ]
        )
        for tariff in tariffs
    ]
