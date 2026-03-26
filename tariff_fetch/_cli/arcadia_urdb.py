import json
import shlex
from datetime import date
from pathlib import Path
from typing import cast, get_args

from dotenv import load_dotenv

from tariff_fetch import questionary_typed as q

# from tariff_fetch.genability.lse import get_lses_page
# from tariff_fetch.genability.tariffs import CustomerClass, TariffType, tariffs_paginate
from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import CustomerClass, RateChargeClass, TariffType
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyStandard
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.prompts import prompt_charge_classes
from tariff_fetch.urdb.arcadia.scenario import Scenario, ScenarioPropertyValue
from tariff_fetch.urdb.schema import URDBRate

from . import console, prompt_filename
from .types import Utility

_ALL_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))
_CHARGE_CLASS_CODES: tuple[tuple[str, RateChargeClass], ...] = (
    ("S", "SUPPLY"),
    ("T", "TRANSMISSION"),
    ("D", "DISTRIBUTION"),
    ("t", "TAX"),
    ("C", "CONTRACTED"),
    ("U", "USER_ADJUSTED"),
    ("A", "AFTER_TAX"),
    ("O", "OTHER"),
    ("N", "NON_BYPASSABLE"),
    ("n", "NET_EXCESS"),
)


def process_genability(
    utility: Utility,
    output_folder: Path,
    year: int,
    interactive_errors: bool,
    properties: dict[str, ScenarioPropertyValue] | None = None,
):
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
    replay_commands: list[str] = []

    # tariff_ids = {id_ for _, id_ in tariffs}

    apply_percentages = q.confirm("Apply percentage rates?").ask_or_exit()

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
            properties=properties or {},
        )
        urdb_tariff = build_urdb(api, scenario, interactive_errors=interactive_errors)
        urdb_tariff["name"] = _prompt_tariff_name(urdb_tariff.get("name", ""))

        results.append(urdb_tariff)
        replay_commands.append(_format_replay_command(scenario, tariff))
        # results.append(build_urdb(tariff, api, scenario))

    suggested_filename = f"arcadia_{utility.name}.urdb.{year}."

    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return

    filename.parent.mkdir(exist_ok=True)
    _ = filename.write_text(json.dumps({"items": results}, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {filename}")
    if replay_commands:
        console.print("Replay with `tariff-fetch urdb ni`:")
        for command in replay_commands:
            console.print(command)


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
        choices: list[q.Choice[int | None] | q.Separator] = [
            q.Choice(title=lse["name"], value=lse["lse_id"]) for lse in lses
        ]
        choices.append(q.Separator())
        choices.append(q.Choice(title="None of these", value=None))
        utility_lse_id = q.select(
            message=f"Found multiple utilities with lse id = {utility.eia_id}. Select one.", choices=choices
        ).ask()
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
    result = q.checkbox(
        message="Select tariffs",
        choices=[
            q.Choice(
                title=f"{tariff_['tariff_name']} ({tariff_['master_tariff_id']})",
                value=(tariff_["tariff_name"], tariff_["master_tariff_id"]),
                checked=True,
            )
            for tariff_ in tariffs
        ],
        use_search_filter=True,
        use_jk_keys=False,
    ).ask_or_exit()
    return result


def _select_customer_classes() -> list[CustomerClass]:
    choices: list[q.Choice[CustomerClass]] = [
        q.Choice(title="Residential", value="RESIDENTIAL"),
        q.Choice(title="General", value="GENERAL"),
        q.Choice(title="Special Use", value="SPECIAL_USE"),
    ]
    result = q.checkbox(
        message="Select customer classes",
        choices=choices,
        validate=lambda items: True if items else "Select at least one customer class",
    ).ask_or_exit()
    return result


def _select_tariff_types() -> list[TariffType]:
    choices: list[q.Choice[TariffType]] = [
        q.Choice(title="Default", value="DEFAULT"),
        q.Choice(title="Alternative", value="ALTERNATIVE"),
        q.Choice(title="Optional extra", value="OPTIONAL_EXTRA"),
        q.Choice(title="Rider", value="RIDER"),
    ]
    result = q.checkbox(
        message="Select tariff types",
        choices=choices,
        validate=lambda items: bool(items) or "Select at least one tariff type",
    ).ask_or_exit()
    return result


def _fetch_tariffs(api: ArcadiaSignalAPI, tariffs: list[tuple[str, int]], year: int):
    result: list[TariffExtended] = []
    with console.status("Fetching tariffs..."):
        for name, id_ in tariffs:
            console.print(f"Master tariff id: {id_} ({name})")
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
    return q.text("Tariff name", default=default).ask_or_exit()


def _format_replay_command(scenario: Scenario, tariff: TariffExtended) -> str:
    parts = ["tariff-fetch", "urdb", "ni", str(scenario.master_tariff_id), str(scenario.year)]
    if not scenario.apply_percentages:
        parts.append("--no-apply-percentages")

    charge_class_flags = _format_charge_class_flags(scenario.charge_classes)
    parts.extend(charge_class_flags)

    for key, value in sorted(_canonicalize_properties(scenario.properties, tariff).items()):
        values = value if isinstance(value, list) else [value]
        for item in values:
            parts.extend(["--property", f"{key}={_format_property_value(item)}"])

    return shlex.join(parts)


def _format_charge_class_flags(charge_classes: set[RateChargeClass]) -> list[str]:
    if charge_classes == set(_ALL_CHARGE_CLASSES):
        return []

    shortcut = "".join(code for code, charge_class in _CHARGE_CLASS_CODES if charge_class in charge_classes)
    return ["-cc", shortcut]


def _canonicalize_properties(
    properties: dict[str, ScenarioPropertyValue], tariff: TariffExtended
) -> dict[str, ScenarioPropertyValue]:
    canonical: dict[str, ScenarioPropertyValue] = {}
    consumed_keys: set[str] = set()
    property_defs = tariff.get("properties", [])

    for tariff_property in property_defs:
        matches = _find_matching_property_keys(properties, tariff_property)
        key_name = tariff_property["key_name"]
        if key_name in properties:
            canonical[key_name] = properties[key_name]
            consumed_keys.add(key_name)
            continue
        if matches:
            canonical[key_name] = properties[matches[0]]
            consumed_keys.update(matches)

    for key, value in properties.items():
        if key not in consumed_keys and key not in canonical:
            canonical[key] = value
    return canonical


def _find_matching_property_keys(
    properties: dict[str, ScenarioPropertyValue], tariff_property: TariffPropertyStandard
) -> list[str]:
    key_name = tariff_property["key_name"]
    display_name = tariff_property["display_name"]
    aliases = {_normalize_property_alias(key_name), _normalize_property_alias(display_name)}
    return [candidate for candidate in properties if _normalize_property_alias(candidate) in aliases]


def _normalize_property_alias(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _format_property_value(value: ScenarioPropertyValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
