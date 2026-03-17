import json
from datetime import date
from pathlib import Path
from typing import cast

import questionary
from dotenv import load_dotenv

# from tariff_fetch.genability.lse import get_lses_page
# from tariff_fetch.genability.tariffs import CustomerClass, TariffType, tariffs_paginate
from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import CustomerClass, TariffType
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.prompts import prompt_charge_classes
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tariff_fetch.urdb.schema import URDBRate

from . import console, prompt_filename
from .types import Utility


def process_genability(utility: Utility, output_folder: Path, year: int, interactive_errors: bool):
    _ = load_dotenv()
    api = ArcadiaSignalAPI()

    lse_id = _find_utility_lse_id(api, utility)
    if lse_id is None:
        return

    if not (customer_classes := _select_customer_classes()):
        return

    if not (tariff_types := _select_tariff_types()):
        return

    if not (tariffs := _select_tariffs(api, lse_id, customer_classes, tariff_types, year)):
        console.print("[red]No tariffs found[/]")
        _ = console.input("Press enter to proceed...")
        return

    api_results = _fetch_tariffs(api, tariffs, year)
    results: list[URDBRate] = []

    # tariff_ids = {id_ for _, id_ in tariffs}

    apply_percentages = cast(bool | None, questionary.confirm("Apply percentage rates?").ask())
    if apply_percentages is None:
        return

    for tariff in api_results:
        tariff_name = tariff["tariff_name"]
        console.print(f"Creating scenario for tariff: [blue]{tariff_name}[/]")
        charge_classes = prompt_charge_classes()
        if charge_classes is None:
            continue
        scenario = Scenario(
            tariff["master_tariff_id"],
            year=year,
            apply_percentages=apply_percentages,
            charge_classes=charge_classes,
        )
        urdb_tariff = build_urdb(api, scenario, interactive_errors=interactive_errors)
        urdb_tariff["name"] = _prompt_tariff_name(urdb_tariff.get("name", ""))

        results.append(urdb_tariff)
        # results.append(build_urdb(tariff, api, scenario))

    suggested_filename = f"arcadia_{utility.name}.urdb.{year}."

    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return

    filename.parent.mkdir(exist_ok=True)
    _ = filename.write_text(json.dumps({"items": results}, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {filename}")


def _find_utility_lse_id(api: ArcadiaSignalAPI, utility: Utility) -> int | None:
    with console.status("Fetching lses..."):
        lses = api.lses.get_page(
            fields="min",
            search_on=["code"],
            search=str(utility.eia_id),
            starts_with=True,
            ends_with=True,
        )["results"]
    if len(lses) == 0:
        # No utilities found with this eia id
        console.print(
            f'Utility "{utility.name}" with EIA Id {utility.eia_id} not found in arcadia database', style="bold red"
        )
        return None
    if len(lses) == 1:
        # Found one utility
        utility_lse_id = lses[0]["lse_id"]
        return utility_lse_id
    else:
        # Nothing found; this should *theoretically* never happen but let's keep it just in case
        choices = [questionary.Choice(title=_["name"], value=_["lse_id"]) for _ in lses]
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(title="None of these", value=None))
        utility_lse_id = cast(
            int | None,
            questionary.select(
                message=f"Found multiple utilities with lse id = {utility.eia_id}. Select one.", choices=choices
            ).ask(),
        )
        if utility_lse_id is None:
            console.print("No utility chosen")
            return None
        return utility_lse_id


def _select_tariffs(
    api: ArcadiaSignalAPI, lse_id: int, customer_classes: list[CustomerClass], tariff_types: list[TariffType], year: int
) -> list[tuple[str, int]]:
    with console.status("Fetching tariffs..."):
        tariffs = list(
            api.tariffs.iter_pages(
                lse_id=lse_id,
                effective_on=date(year, 6, 1),
                customer_classes=customer_classes,
                tariff_types=tariff_types,
            )
        )
    if not tariffs:
        return []
    return cast(
        list[tuple[str, int]],
        questionary.checkbox(
            message="Select tariffs",
            choices=[
                questionary.Choice(
                    title=f"{_['tariff_name']} ({_['tariff_id']})",
                    value=(_["tariff_name"], _["master_tariff_id"]),  # pyright: ignore[reportAny]
                    checked=True,
                )
                for _ in tariffs
            ],
            use_search_filter=True,
            use_jk_keys=False,
        ).ask(),
    )


def _select_customer_classes() -> list[CustomerClass]:
    return cast(
        list[CustomerClass],
        questionary.checkbox(
            message="Select customer classes",
            choices=[
                questionary.Choice(title="Residential", value="RESIDENTIAL"),
                questionary.Choice(title="General", value="GENERAL"),
                questionary.Choice(title="Special Use", value="SPECIAL_USE"),
            ],
            validate=lambda _: True if _ else "Select at least one customer class",
        ).ask(),
    )


def _select_tariff_types() -> list[TariffType]:
    return cast(
        list[TariffType],
        questionary.checkbox(
            message="Select tariff types",
            choices=[
                questionary.Choice(title="Default", value="DEFAULT"),
                questionary.Choice(title="Alternative", value="ALTERNATIVE"),
                questionary.Choice(title="Optional extra", value="OPTIONAL_EXTRA"),
                questionary.Choice(title="Rider", value="RIDER"),
            ],
            validate=lambda _: bool(_) or "Select at least one tariff type",
        ).ask(),
    )


def _fetch_tariffs(api: ArcadiaSignalAPI, tariffs: list[tuple[str, int]], year: int):
    result: list[TariffExtended] = []
    with console.status("Fetching tariffs..."):
        for name, id_ in tariffs:
            console.print(f"Tariff id: {name}")
            page = api.tariffs.iter_pages(
                fields="ext",
                master_tariff_id=id_,
                effective_on=date(year, 12, 1),
                populate_properties=True,
                populate_rates=True,
            )
            result.extend(page)
    return result


def _prompt_tariff_name(default: str) -> str:
    result = cast(str | None, questionary.text("Tariff name", default=default).ask())
    if result is None:
        exit()
    return result
