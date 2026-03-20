import json
import os
from collections.abc import Collection
from datetime import date
from pathlib import Path
from statistics import mean
from typing import cast, get_args

import tenacity
from dotenv import load_dotenv
from rich.prompt import Confirm
from selenium.common.exceptions import WebDriverException

from tariff_fetch import questionary_typed as q
from tariff_fetch.rateacuity import LoginState, create_context
from tariff_fetch.urdb.rateacuity_history_gas import (
    build_urdb,
)
from tariff_fetch.urdb.rateacuity_history_gas.history_data import HistoryData, PercentageRow, Row
from tariff_fetch.urdb.schema import RateSector, ServiceType, URDBRate

from . import console, prompt_filename

# TODO: This is ungodly ugly but it works


def process_rateacuity_gas_urdb(output_folder: Path, state: str, year: int):
    _ = load_dotenv()
    if not (username := os.getenv("RATEACUITY_USERNAME")):
        console.print("[b]RATEACUITY_USERNAME[/] environment variable is not set")
    if not (password := os.getenv("RATEACUITY_PASSWORD")):
        console.print("[b]RATEACUITY_PASSWORD[/] environment variable is not set")
    if not (username and password):
        console.print("Cannot use RateAcuity due to missing credentials")
        _ = console.input("Press enter to proceed...")
        return

    selected_utility = None
    tariffs_to_include = None
    result: list[URDBRate] = []
    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_attempt(3), retry=tenacity.retry_if_exception_type(WebDriverException)
    ):
        with attempt, create_context() as context:
            with console.status("Fetching list of utilities..."):
                scraping_state = (
                    LoginState(context).login(username, password).gas().history().select_state(state.upper())
                )
                utilities = [_ for _ in scraping_state.get_utilities() if _]
            if selected_utility is None:
                selected_utility = q.select(
                    message="Select a utility from available choices",
                    choices=utilities,
                    use_jk_keys=False,
                    use_search_filter=True,
                    use_shortcuts=False,
                ).ask()
                if not selected_utility:
                    return
            with console.status("Fetching list of tariffs..."):
                scraping_state = scraping_state.select_utility(selected_utility)
                tariffs = [_ for _ in scraping_state.get_schedules() if _]
            if tariffs_to_include is None:
                tariffs_to_include = q.checkbox(
                    message="Select tariffs to include",
                    choices=tariffs,
                    use_jk_keys=False,
                    use_search_filter=True,
                    validate=lambda items: bool(items) or "Select at least one tariff",
                ).ask()

            if not tariffs_to_include:
                console.print("[red]No tariffs selected[/]")
                _ = console.input("Press enter to proceed...")
                return
            console.print("Fetching tariffs")
            while tariffs_to_include:
                tariff = tariffs_to_include.pop(0)
                console.log(f"Fetching {tariff}")
                scraping_state = (
                    scraping_state.select_schedule(tariff)
                    .set_enddate(date(year, 12, 1))
                    .set_number_of_comparisons(12)
                    .set_frequency(1)
                )
                df = scraping_state.as_dataframe()
                hd = HistoryData(df)
                validation_errors = hd.validate_rows()
                proceed = True
                if validation_errors:
                    console.print("Following rows cannot be processed and will be ignored:")
                    for error in validation_errors:
                        console.print(f" - {error.row}")
                    proceed = Confirm.ask("Proceed?", console=console)

                if proceed and (unknown_non_empty_columns := hd.get_unknown_nonempty_columns()):
                    console.print("Found following unknown non-empty columns. Their values will be ignored:")
                    for col in unknown_non_empty_columns:
                        console.print(f" - {col}")
                    proceed = Confirm.ask("Proceed?", console=console)

                if proceed:
                    apply_percentages = False
                    rows = list(hd.rows())
                    if percentage_columns := _get_percentage_columns(rows):
                        percentage_columns_strings = [
                            f"- {c[0]} ({c[1]}): {c[2]}" if c[1] else f"- {c[0]}: {c[2]}" for c in percentage_columns
                        ]
                        console.print("Found following percentage columns (values are averages over 12 months):")
                        console.print("\n".join(percentage_columns_strings))
                        console.print("It is impossible to tell which percentages apply to which specific rates.")
                        console.print("Percentages will be applied to the final result as is")
                        apply_percentages = Confirm.ask("Apply percentages? (otherwise percentages will be ignored)")

                    label = q.text("Label", default=_utility_name_to_label(selected_utility)).ask()
                    if label is None:
                        exit()
                    sector = q.select(
                        "Sector",
                        default="Residential",
                        choices=get_args(RateSector),
                    ).ask()
                    if sector is None:
                        exit()

                    servicetype = q.select(
                        "Sector",
                        default="Bundled",
                        choices=get_args(ServiceType),
                    ).ask()
                    if servicetype is None:
                        exit()

                    try:
                        urdb = build_urdb(rows, apply_percentages)
                    except ValueError as e:
                        console.print(f"Cannot convert to urdb: [red]{e}[/]")
                    else:
                        urdb["utility"] = selected_utility
                        urdb["name"] = tariff
                        urdb["label"] = label
                        urdb["sector"] = cast(RateSector, sector)
                        urdb["servicetype"] = cast(ServiceType, servicetype)
                        urdb["demandunits"] = "kW"
                        urdb["mincharge"] = 0.0
                        urdb["minchargeunits"] = "$/month"
                        urdb["country"] = "USA"
                        result.append(urdb)

                scraping_state = (
                    scraping_state.back_to_selections()
                    .history()
                    .select_state(state.upper())
                    .select_utility(selected_utility)
                )
    suggested_filename = f"rateacuity_{selected_utility}.urdb.{year}."
    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return
    filename.parent.mkdir(exist_ok=True)
    wrapped_result = {"items": result}
    _ = filename.write_text(json.dumps(wrapped_result, indent=2))


def _utility_name_to_label(utility_name: str) -> str:
    if not utility_name:
        return ""
    return "".join(w[0].lower() for w in utility_name.split() if w)


def _get_percentage_columns(rows: Collection[Row]) -> list[tuple[str, str | None, float]]:
    return [
        (row.rate, row.location, mean(row.month_value_float(month) for month in range(0, 12)))
        for row in rows
        if isinstance(row, PercentageRow)
    ]
