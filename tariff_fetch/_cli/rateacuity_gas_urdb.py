import json
import os
from datetime import date
from pathlib import Path
from typing import cast

import questionary
import tenacity
from dotenv import load_dotenv
from rich.prompt import Confirm
from selenium.common.exceptions import WebDriverException

from tariff_fetch.rateacuity import LoginState, create_context
from tariff_fetch.urdb.rateacuity_history_gas import build_urdb, validate_dataframe
from tariff_fetch.urdb.schema import URDBRate

from . import console, prompt_filename


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
                selected_utility = cast(
                    str,
                    questionary.select(
                        message="Select a utility from available choices",
                        choices=utilities,
                        use_jk_keys=False,
                        use_search_filter=True,
                        use_shortcuts=False,
                    ).ask(),
                )
                if not selected_utility:
                    return
            with console.status("Fetching list of tariffs..."):
                scraping_state = scraping_state.select_utility(selected_utility)
                tariffs = [_ for _ in scraping_state.get_schedules() if _]
            if tariffs_to_include is None:
                tariffs_to_include = cast(
                    list[str],
                    questionary.checkbox(
                        message="Select tariffs to include",
                        choices=tariffs,
                        use_jk_keys=False,
                        use_search_filter=True,
                        validate=lambda _: bool(_) or "Select at least one tariff",
                    ).ask(),
                )

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
                validation_issues = validate_dataframe(df)
                proceed = True
                if validation_issues:
                    console.print("Following issues found in the table:")
                    for issue in validation_issues:
                        console.print(f" - {issue}")
                    proceed = Confirm.ask("Proceed?", console=console)
                if proceed:
                    urdb = build_urdb(df)
                    urdb["utility"] = selected_utility
                    urdb["name"] = tariff
                    result.append(urdb)

                scraping_state = (
                    scraping_state.back_to_selections()
                    .history()
                    .select_state(state.upper())
                    .select_utility(selected_utility)
                )
    suggested_filename = f"rateacuity_{selected_utility}"
    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return
    filename.parent.mkdir(exist_ok=True)
    _ = filename.write_text(json.dumps(result, indent=2))
