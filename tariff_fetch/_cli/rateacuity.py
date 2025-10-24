import json
import os
from pathlib import Path

import questionary
import tenacity
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from selenium.common.exceptions import WebDriverException

from tariff_fetch._cli.types import Utility
from tariff_fetch.rateacuity import LoginState, create_context

from . import console, prompt_filename


def process_rateacuity_gas(output_folder: Path, state: str):
    load_dotenv()
    if not (username := os.getenv("RATEACUITY_USERNAME")):
        raise ValueError("RATEACUITY_USERNAME variable is not set")
    if not (password := os.getenv("RATEACUITY_PASSWORD")):
        raise ValueError("RATEACUITY_PASSWORD variable is not set")

    selected_utility = None
    tariffs_to_include = None
    results = []

    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_attempt(3), retry=tenacity.retry_if_exception_type(WebDriverException)
    ):
        with attempt, create_context() as context:
            with console.status("Fetching list of utilities..."):
                scraping_state = (
                    LoginState(context).login(username, password).gas().benchmark_all().select_state(state.upper())
                )
                utilities = [_ for _ in scraping_state.get_utilities() if _]

            if not utilities:
                raise RuntimeError(f"Something's wrong: rateacuity shows no utilities for this state ({state})")

            if selected_utility is None:
                selected_utility = questionary.select(
                    message="Select a utility from available choices",
                    choices=utilities,
                    use_jk_keys=False,
                    use_search_filter=True,
                    use_shortcuts=False,
                ).ask()
                if not selected_utility:
                    console.print("[red]cancelled[/]")
                    return

            with console.status("Fetching list of tariffs..."):
                scraping_state = scraping_state.select_utility(selected_utility)
                tariffs = [_ for _ in scraping_state.get_schedules() if _]

            if tariffs_to_include is None:
                tariffs_to_include = questionary.checkbox(
                    message="Select tariffs to include",
                    choices=tariffs,
                    use_jk_keys=False,
                    use_search_filter=True,
                    validate=lambda _: bool(_) or "Select at least one tariff",
                ).ask()

            if not tariffs_to_include:
                console.print("[red]No tariffs selected[/]")
                console.input("Press enter to proceed...")
                return

            with console.status("Fetching tariffs..."):
                while tariffs_to_include:
                    tariff = tariffs_to_include.pop(0)
                    console.log(f"Fetching {tariff}")
                    scraping_state = scraping_state.select_schedule(tariff)
                    sections = scraping_state.as_sections()
                    results.append({"schedule": tariff, "sections": sections})
                    scraping_state = scraping_state.back_to_selections()

    assert selected_utility
    suggested_filename = f"gas_rateacuity_{selected_utility}"
    filename = prompt_filename(output_folder, suggested_filename, "json")
    filename.parent.mkdir(exist_ok=True)
    filename.write_text(json.dumps(results, indent=2))


def process_rateacuity(output_folder: Path, state: str, utility: Utility):
    load_dotenv()
    if not (username := os.getenv("RATEACUITY_USERNAME")):
        raise ValueError("RATEACUITY_USERNAME variable is not set")
    if not (password := os.getenv("RATEACUITY_PASSWORD")):
        raise ValueError("RATEACUITY_PASSWORD variable is not set")

    selected_utility = None
    tariffs_to_include = None
    results = []

    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_attempt(3), retry=tenacity.retry_if_exception_type(WebDriverException)
    ):
        with attempt, create_context() as context:
            with console.status("Fetching list of utilities..."):
                scraping_state = (
                    LoginState(context).login(username, password).electric().benchmark_all().select_state(state.upper())
                )
                utilities = [_ for _ in scraping_state.get_utilities() if _]

            if not utilities:
                raise RuntimeError(f"Something's wrong: rateacuity shows no utilities for this state ({state})")

            if selected_utility is None:
                utilities_scored = sorted(utilities, key=lambda _: fuzz.ratio(utility.name, _), reverse=True)
                selected_utility = utilities_scored.pop(0)
                if not questionary.confirm(f"Is this the correct utility: {selected_utility} ?").ask():
                    selected_utility = questionary.select(
                        message="Select a utility from available choices",
                        choices=utilities_scored,
                        use_jk_keys=False,
                        use_search_filter=True,
                        use_shortcuts=False,
                    ).ask()
                if not selected_utility:
                    console.print("[red]cancelled[/]")

            with console.status("Fetching list of tariffs..."):
                scraping_state = scraping_state.select_utility(selected_utility)
                tariffs = [_ for _ in scraping_state.get_schedules() if _]

            if tariffs_to_include is None:
                tariffs_to_include = questionary.checkbox(
                    message="Select tariffs to include",
                    choices=tariffs,
                    use_jk_keys=False,
                    use_search_filter=True,
                    validate=lambda _: bool(_) or "Select at least one tariff",
                ).ask()

            if not tariffs_to_include:
                console.print("[red]No tariffs selected[/]")
                console.input("Press enter to proceed...")
                return

            with console.status("Fetching tariffs..."):
                while tariffs_to_include:
                    tariff = tariffs_to_include.pop(0)
                    console.log(f"Fetching {tariff}")
                    scraping_state = scraping_state.select_schedule(tariff)
                    sections = scraping_state.as_sections()
                    results.append({"schedule": tariff, "sections": sections})
                    scraping_state = scraping_state.back_to_selections()

    assert selected_utility
    suggested_filename = f"rateacuity_{selected_utility}"
    filename = prompt_filename(output_folder, suggested_filename, "json")
    filename.parent.mkdir(exist_ok=True)
    filename.write_text(json.dumps(results, indent=2))
