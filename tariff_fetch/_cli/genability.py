import json
from datetime import datetime, timezone
from pathlib import Path

import questionary
from dotenv import load_dotenv

from tariff_fetch.genability.lse import get_lses_page
from tariff_fetch.genability.tariffs import CustomerClass, TariffType, tariffs_paginate

from . import console, prompt_filename
from .types import Utility


def _find_utility_lse_id(utility: Utility) -> int | None:
    with console.status("Fetching lses..."):
        lses = get_lses_page(
            fields="min",
            searchOn=["code"],
            search=str(utility.eia_id),
            startsWith=True,
            endsWith=True,
        )["results"]
    if len(lses) == 0:
        # No utilities found with this eia id
        console.print(
            f'Utility "{utility.name}" with EIA Id {utility.eia_id} not found in arcadia database', style="bold red"
        )
        return None
    if len(lses) == 1:
        # Found one utility
        utility_lse_id = lses[0]["lseId"]
        return utility_lse_id
    else:
        # Nothing found; this should *theoretically* never happen but let's keep it just in case
        choices = [questionary.Choice(title=_["name"], value=_["lseId"]) for _ in lses]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="None of these", value=None))
        utility_lse_id: int | None = questionary.select(
            message=f"Found multiple utilities with lse id = {utility.eia_id}. Select one.", choices=choices
        ).ask()
        if utility_lse_id is None:
            console.print("No utility chosen")
            return None
        return utility_lse_id


def _select_tariffs(
    lse_id: int, customer_classes: list[CustomerClass], tariff_types: list[TariffType]
) -> list[tuple[str, int]]:
    with console.status("Fetching tariffs..."):
        tariffs = list(
            tariffs_paginate(
                lseId=lse_id,
                fields="min",
                effectiveOn=datetime.now(timezone.utc),
                customerClasses=customer_classes,
                tariffTypes=tariff_types,
            )
        )
    if not tariffs:
        return []
    return questionary.checkbox(
        message="Select tariffs",
        choices=[
            questionary.Choice(title=_["tariffName"], value=(_["tariffName"], _["masterTariffId"]), checked=True)
            for _ in tariffs
        ],
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()


def _select_customer_classes() -> list[CustomerClass]:
    return questionary.checkbox(
        message="Select customer classes",
        choices=[
            questionary.Choice(title="Residential", value="RESIDENTIAL"),
            questionary.Choice(title="General", value="GENERAL"),
            questionary.Choice(title="Special Use", value="SPECIAL_USE"),
        ],
        validate=lambda _: True if _ else "Select at least one customer class",
    ).ask()


def _select_tariff_types() -> list[TariffType]:
    return questionary.checkbox(
        message="Select tariff types",
        choices=[
            questionary.Choice(title="Default", value="DEFAULT"),
            questionary.Choice(title="Alternative", value="ALTERNATIVE"),
            questionary.Choice(title="Optional extra", value="OPTIONAL_EXTRA"),
            questionary.Choice(title="Rider", value="RIDER"),
        ],
        validate=lambda _: bool(_) or "Select at least one tariff type",
    ).ask()


def _fetch_tariffs(tariffs: list[tuple[str, int]]):
    result = []
    with console.status("Fetching tariffs..."):
        for name, id_ in tariffs:
            console.print(f"Tariff id: {name}")
            page = list(
                tariffs_paginate(
                    masterTariffId=id_,
                    effectiveOn=datetime.now(timezone.utc),
                    fields="ext",
                    populateProperties=True,
                    populateRates=True,
                )
            )
            result.extend(page)
    return result


def process_genability(utility: Utility, output_folder: Path):
    load_dotenv()
    lse_id = _find_utility_lse_id(utility)
    if lse_id is None:
        console.input("Press enter to proceed...")
        return
    customer_classes = _select_customer_classes()
    tariff_types = _select_tariff_types()
    tariffs = _select_tariffs(lse_id, customer_classes, tariff_types)
    if not tariffs:
        console.print("[red]No tariffs found[/]")
        console.input("Press enter to proceed...")
        return
    results = _fetch_tariffs(tariffs)
    suggested_filename = f"arcadia_{utility.name}"
    filename = prompt_filename(output_folder, suggested_filename, "json")
    filename.parent.mkdir(exist_ok=True)
    filename.write_text(json.dumps(results, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {filename}")
