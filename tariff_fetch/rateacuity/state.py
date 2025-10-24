"""State-machine style helpers for navigating the RateAcuity portal.

The module exposes a small set of classes that wrap Selenium interactions and
provide a linear flow for logging in, picking reporting parameters, and
downloading prepared benchmark reports as Polars dataframes.

Usage
-----
    from tariff_fetch.rateacuity.base import create_context
    from tariff_fetch.rateacuity.state import LoginState

    with create_context() as context:
        report = (
            LoginState(context)
            .login(username, password)
            .electric()
            .benchmark()
            .select_state("NY")
            .select_utility("Consolidated Edison Company of New York")
            .select_schedule("Residential Service")
        )
        df = report.as_dataframe()

The resulting ``df`` contains the cleaned benchmark data for the selected
schedule.
"""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from time import sleep
from typing import TypeVar

import polars as pl
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from tariff_fetch.rateacuity.report_tables import SectionJson, sections_to_json

from .base import ScrapingContext, create_context, login

logger = logging.getLogger(__name__)


class State:
    """Shared Selenium helpers as the base for the strongly-typed state objects."""

    def __init__(self, context: ScrapingContext):
        """Store the scraping context that contains the shared webdriver."""
        self._context = context

    @property
    def driver(self) -> Chrome:
        """Expose the underlying Selenium driver used for navigation."""
        return self._context.driver

    def _logged_in(self) -> bool:
        """Return True if the login link is absent, indicating an authenticated session."""
        return not self.driver.find_elements(By.ID, "loginLink")

    def _wait(self) -> WebDriverWait:
        """Create a wait helper bound to the current driver instance."""
        return WebDriverWait(self.driver, 10)


S = TypeVar("S", bound=State)


class LoginState(State):
    def login(self, username: str, password: str) -> PortalState:
        """Authenticate with RateAcuity and transition into the portal state."""
        login(self._context.driver, username, password)
        return PortalState(self._context)


class PortalState(State):
    def electric(self) -> ElectricState:
        """Navigate to the Electric entry point of the portal."""
        logger.info("Going to electric")
        self.driver.get("https://secure.rateacuity.com/RateAcuity/ElecEntry/IndexViews")
        return ElectricState(self._context)


class SelectReportState(State):
    def _select_report(self, report: str):
        """Click the given radio report selector if it is not already active."""
        radio = self._wait().until(
            EC.presence_of_element_located((By.XPATH, f'//input[@id="report" and @value="{report}"]'))
        )
        if not radio.is_selected():
            radio.click()


class ElectricState(SelectReportState):
    def benchmark(self) -> ElectricBenchmarkStateDropdown:
        """Switch the Electric report type to Benchmark and expose the state dropdown."""
        self._select_report("benchmark")
        return ElectricBenchmarkStateDropdown(self._context)

    def benchmark_all(self) -> ElectricBenchmarkAllStateDropdown:
        self._select_report("benchall")
        return ElectricBenchmarkAllStateDropdown(self._context)


class DropdownState(State):
    """Shared behavior for dropdown-driven selections on the benchmark workflow."""

    element_id: str

    def _dropdown(self):
        return self._wait().until(EC.presence_of_element_located((By.ID, self.element_id)))

    def _visible_options(self) -> list[str]:
        dropdown = self._dropdown()
        return [option.text for option in dropdown.find_elements(By.TAG_NAME, "option")]

    def _select(self, choice: str, *, category: str, next_state: S) -> S:
        raw_options = self._visible_options()
        normalized = {option.strip(): option for option in raw_options}
        stripped_choice = choice.strip()

        if choice in raw_options:
            visible_choice = choice
            normalized_choice = stripped_choice
        elif stripped_choice in normalized:
            visible_choice = normalized[stripped_choice]
            normalized_choice = stripped_choice
        else:
            raise ValueError(f"{category} {choice} is invalid. Available options are: {list(normalized)}")

        dropdown = self._dropdown()
        select = Select(dropdown)
        current = select.first_selected_option.text.strip() if select.first_selected_option else None
        if current != normalized_choice:
            logger.info(f"Selecting {category.lower()} {normalized_choice}")
            select.select_by_visible_text(visible_choice)
        return next_state


class ElectricBenchmarkAllStateDropdown(DropdownState):
    element_id = "StateSelect"

    def get_states(self) -> list[str]:
        return self._visible_options()

    def select_state(self, state: str) -> ElectricBenchmarkAllUtilityDropdown:
        return self._select(state, category="State", next_state=ElectricBenchmarkAllUtilityDropdown(self._context))


class ElectricBenchmarkAllUtilityDropdown(ElectricBenchmarkAllStateDropdown):
    element_id = "UtilitySelect"

    def get_utilities(self) -> list[str]:
        return self._visible_options()

    def select_utility(self, utility: str) -> ElectricBenchmarkAllScheduleDropdown:
        return self._select(utility, category="Utility", next_state=ElectricBenchmarkAllScheduleDropdown(self._context))


class ElectricBenchmarkAllScheduleDropdown(ElectricBenchmarkAllUtilityDropdown):
    element_id = "ScheduleSelect"

    def get_schedules(self) -> list[str]:
        return self._visible_options()

    def select_schedule(self, schedule: str) -> ElectricBenchmarkAllReport:
        """Select a schedule and produce a report interface that can fetch data."""
        return self._select(schedule, category="Schedule", next_state=ElectricBenchmarkAllReport(self._context))


class ElectricBenchmarkStateDropdown(DropdownState):
    element_id = "StateSelect"

    def get_states(self) -> list[str]:
        """Return all available states visible in the State dropdown."""
        return self._visible_options()

    def select_state(self, state: str) -> ElectricBenchmarkUtilityDropdown:
        """Select the provided state and transition to the utility dropdown."""
        return self._select(state, category="State", next_state=ElectricBenchmarkUtilityDropdown(self._context))


class ElectricBenchmarkUtilityDropdown(ElectricBenchmarkStateDropdown):
    element_id = "UtilitySelect"

    def get_utilities(self) -> list[str]:
        """Return all available utilities for the previously chosen state."""
        return self._visible_options()

    def select_utility(self, utility: str) -> ElectricBenchmarkScheduleDropdown:
        """Select the provided utility and expose the schedule dropdown."""
        return self._select(utility, category="Utility", next_state=ElectricBenchmarkScheduleDropdown(self._context))


class ElectricBenchmarkScheduleDropdown(ElectricBenchmarkUtilityDropdown):
    element_id = "ScheduleSelect"

    def get_schedules(self) -> list[str]:
        """Return all schedules associated with the selected utility."""
        return self._visible_options()

    def select_schedule(self, schedule: str) -> ElectricBenchmarkReport:
        """Select a schedule and produce a report interface that can fetch data."""
        return self._select(schedule, category="Schedule", next_state=ElectricBenchmarkReport(self._context))


class ReportState(State):
    def _back_to_selections(self, state: S) -> S:
        self._wait().until(EC.presence_of_element_located((By.LINK_TEXT, "Back To Selections"))).click()
        return state

    def download_excel(self, timeout: int = 20) -> Path:
        """Trigger the report download and return the path once it appears."""
        self._wait().until(EC.presence_of_element_located((By.XPATH, '//a[text()="Create Excel Spreadsheet"]'))).click()
        download_path = self._context.download_path
        initial_state = _get_xlsx(download_path)

        n = timeout
        while _get_xlsx(download_path) == initial_state and n:
            sleep(1)
            n -= 1

        filename = next(iter(_get_xlsx(download_path) ^ initial_state))
        return Path(download_path, filename)

    def as_sections(self) -> list[SectionJson]:
        return sections_to_json(self._context.driver)

    def as_dataframe(self, timeout: int = 20) -> pl.DataFrame:
        """Convert a freshly downloaded Excel report into a cleaned Polars dataframe."""
        filepath = self.download_excel(timeout)
        logger.info(f"Reading excel file {filepath}")
        raw_data = pl.read_excel(filepath, engine="calamine", has_header=False)
        header_row_index = next(i for i, row in enumerate(raw_data.iter_rows()) if "Component Description" in row[0])
        df = pl.read_excel(filepath, engine="calamine", read_options={"header_row": header_row_index})
        df = df.with_columns(
            [
                pl.when(pl.col(c).cast(pl.Utf8).str.strip_chars() == "").then(None).otherwise(pl.col(c)).alias(c)
                for c in df.columns
            ]
        )
        df = df.filter(pl.col(df.columns[0]).is_not_null() & pl.col(df.columns[1]).is_not_null())
        filepath.unlink()
        return df


class ElectricBenchmarkReport(ReportState):
    def back_to_selections(self) -> ElectricBenchmarkScheduleDropdown:
        """Return to the selections page so additional schedules can be fetched."""
        return self._back_to_selections(ElectricBenchmarkScheduleDropdown(self._context))


class ElectricBenchmarkAllReport(ReportState):
    def back_to_selections(self) -> ElectricBenchmarkAllScheduleDropdown:
        """Return to the selections page so additional schedules can be fetched."""
        return self._back_to_selections(ElectricBenchmarkAllScheduleDropdown(self._context))


def _get_xlsx(folder) -> set[str]:
    """Return the set of .xlsx filenames currently present in the provided folder."""
    return {_ for _ in os.listdir(folder) if _.endswith(".xlsx")}


def main(argv: Sequence[str] | None = None):
    """Fetch residential benchmark schedules for a hard-coded utility and state."""
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Fetch RateAcuity utility rates")
    parser.add_argument(
        "--username",
        default=os.getenv("RATEACUITY_USERNAME"),
        help="Rateacuity Username (defaults to RATEACUITY_USERNAME environment variable)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("RATEACUITY_PASSWORD"),
        help="RateAcuity password (defaults to RATEACUITY_PASSWORD environment variable)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="rateacuity_utility_rates.csv",
        help="Path to write the fetched rates (default: %(default)s).",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    username = args.username
    if not username:
        parser.error("Username must be provided via --username or RATEACUITY_USERNAME environment variable")
    password = args.password
    if not password:
        parser.error("Password must be provided via --password or RATEACUITY_PASSWORD environment variable")

    UTILITY = "Consolidated Edison Company of New York"
    STATE = "NY"

    with create_context() as context:
        state = (
            LoginState(context)
            .login(username, password)
            .electric()
            .benchmark()
            .select_state(STATE)
            .select_utility(UTILITY)
        )
        schedules = state.get_schedules()
        filtered = [_ for _ in schedules if "residential" in _.lower()]

        frames = []

        for schedule in filtered:
            if "residential" not in schedule.lower():
                continue
            state = state.select_schedule(schedule)
            df = state.as_dataframe()
            df = df.with_columns(pl.lit(schedule).alias("Schedule"))
            df = df.select(["Schedule", *[name for name in df.columns if name != "Schedule"]])
            frames.append(df)

            state = state.back_to_selections()

        output_path = Path(args.output)
        combined_df = pl.concat(frames, how="diagonal_relaxed", rechunk=True) if frames else pl.DataFrame()
        combined_df.write_csv(output_path)


if __name__ == "__main__":
    main()
