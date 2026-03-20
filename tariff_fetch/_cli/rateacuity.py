import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path

import tenacity
from dotenv import load_dotenv
from fuzzywuzzy import fuzz  # pyright: ignore[reportMissingTypeStubs]
from selenium.common.exceptions import WebDriverException

from tariff_fetch import questionary_typed as q
from tariff_fetch._cli.types import Utility
from tariff_fetch.rateacuity import LoginState, create_context
from tariff_fetch.rateacuity.schema import Tariff

from . import console, prompt_filename

logger = logging.getLogger(__name__)


def _rateacuity_match_score(query: str, choice: str) -> int:
    return int(fuzz.ratio(query.lower(), choice.lower()))  # pyright: ignore[reportUnknownMemberType]


def _rank_rateacuity_choices(query: str, choices: Sequence[str]) -> list[str]:
    return sorted(choices, key=lambda choice: (_rateacuity_match_score(query, choice), choice.lower()), reverse=True)


def _match_rateacuity_choice(*, query: str, choices: Sequence[str], category: str) -> str:
    ranked_choices = _rank_rateacuity_choices(query, choices)
    if not ranked_choices:
        raise RuntimeError(f"RateAcuity shows no {category.lower()} choices for this selection")
    match = ranked_choices[0]
    logger.info("Matched RateAcuity %s query %r to %r", category.lower(), query, match)
    return match


def _match_rateacuity_choices(*, queries: Sequence[str], choices: Sequence[str], category: str) -> list[str]:
    selected_choices: list[str] = []
    for query in queries:
        match = _match_rateacuity_choice(query=query, choices=choices, category=category)
        if match not in selected_choices:
            selected_choices.append(match)
    return selected_choices


def process_rateacuity_gas(output_folder: Path, state: str):
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
    results: list[Tariff] = []

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
                selected_utility = q.select(
                    message="Select a utility from available choices",
                    choices=utilities,
                    use_jk_keys=False,
                    use_search_filter=True,
                    use_shortcuts=False,
                ).ask_or_exit()

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
                ).ask_or_exit()

            if not tariffs_to_include:
                console.print("[red]No tariffs selected[/]")
                _ = console.input("Press enter to proceed...")
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
    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return
    filename.parent.mkdir(exist_ok=True)
    _ = filename.write_text(json.dumps(results, indent=2))


def process_rateacuity(output_folder: Path, state: str, utility: Utility):
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
    results: list[Tariff] = []

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
                utilities_scored = _rank_rateacuity_choices(utility.name, utilities)
                selected_utility = utilities_scored.pop(0)
                confirmed = q.confirm(f"Is this the correct utility: {selected_utility} ?").ask_or_exit()
                if not confirmed:
                    selected_utility = q.select(
                        message="Select a utility from available choices",
                        choices=utilities_scored,
                        use_jk_keys=False,
                        use_search_filter=True,
                        use_shortcuts=False,
                    ).ask_or_exit()

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
                ).ask_or_exit()

            if not tariffs_to_include:
                console.print("[red]No tariffs selected[/]")
                _ = console.input("Press enter to proceed...")
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
    if not (filename := prompt_filename(output_folder, suggested_filename, "json")):
        return
    filename.parent.mkdir(exist_ok=True)
    _ = filename.write_text(json.dumps(results, indent=2))


def fetch_rateacuity_tariffs(
    *, state: str, utility_query: str, tariff_queries: Sequence[str]
) -> tuple[str, list[Tariff]]:
    _ = load_dotenv()
    username = os.getenv("RATEACUITY_USERNAME")
    password = os.getenv("RATEACUITY_PASSWORD")
    if not username:
        raise ValueError("RATEACUITY_USERNAME environment variable is not set")
    if not password:
        raise ValueError("RATEACUITY_PASSWORD environment variable is not set")

    selected_utility = ""
    results: list[Tariff] = []

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

            selected_utility = _match_rateacuity_choice(query=utility_query, choices=utilities, category="Utility")

            with console.status("Fetching list of tariffs..."):
                scraping_state = scraping_state.select_utility(selected_utility)
                tariffs = [_ for _ in scraping_state.get_schedules() if _]

            selected_tariffs = _match_rateacuity_choices(
                queries=tariff_queries,
                choices=tariffs,
                category="Tariff",
            )

            with console.status("Fetching tariffs..."):
                for tariff in selected_tariffs:
                    console.log(f"Fetching {tariff}")
                    scraping_state = scraping_state.select_schedule(tariff)
                    sections = scraping_state.as_sections()
                    results.append({"schedule": tariff, "sections": sections})
                    scraping_state = scraping_state.back_to_selections()

    return selected_utility, results
