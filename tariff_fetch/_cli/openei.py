import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import questionary
from dotenv import load_dotenv

from tariff_fetch.openei.utility_rates import UtilityRateSector, UtilityRatesResponseItem, iter_utility_rates

from . import console, prompt_filename
from .types import Utility


def _prompt_sector() -> UtilityRateSector:
    return questionary.select(
        message="Select sector",
        choices=[
            "Residential",
            "Commercial",
            "Industrial",
            "Lighting",
        ],
    ).ask()


def _prompt_detail_level() -> Literal["full", "minimal"]:
    return questionary.select(
        message="Select level of detail",
        choices=["full", "minimal"],
    ).ask()


def _get_tariffs(
    eia_id: int, sector: UtilityRateSector, detail: Literal["full", "minimal"]
) -> list[UtilityRatesResponseItem]:
    api_key = os.getenv("OPENEI_API_KEY")
    if not api_key:
        raise ValueError("API Key is not set (via OPENEI_API_KEY variable)")
    with console.status("Fetching rates..."):
        iterator = iter_utility_rates(
            api_key,
            effective_on_date=datetime.now(timezone.utc),
            sector=sector,
            detail=detail,
            eia=eia_id,
        )
        return list(iterator)


def _prompt_tariffs(tariffs: list[UtilityRatesResponseItem]) -> list[UtilityRatesResponseItem]:
    return questionary.checkbox(
        message="Select tariffs to include",
        choices=[questionary.Choice(title=_["name"], value=_, checked=True) for _ in tariffs],
    ).ask()


def process_openei(utility: Utility, output_folder: Path):
    load_dotenv()
    sector = _prompt_sector()
    detail_level = _prompt_detail_level()
    tariffs = _get_tariffs(utility.eia_id, sector, detail_level)
    if not tariffs:
        console.print("[red]No tariffs found[/]")
        console.input("Press enter to proceed...")
        return
    tariffs = _prompt_tariffs(tariffs)
    if not tariffs:
        console.print("[red]No tariffs selected[/]")
        console.input("Press enter to proceed...")
        return

    suggested_filename = f"openei_{utility.name}_{sector}_{detail_level}"
    filepath = prompt_filename(output_folder, suggested_filename, "json")
    filepath.parent.mkdir(exist_ok=True)
    print(filepath)
    filepath.write_text(json.dumps(tariffs, indent=2))
    console.print(f"Wrote [blue]{len(tariffs)}[/] items to {filepath}")
