from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from time import sleep

import polars as pl
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .base import ScrapingContext, create_context, login

logger = logging.getLogger(__name__)


class State:
    def __init__(self, context: ScrapingContext):
        self._context = context

    @property
    def driver(self) -> Chrome:
        return self._context.driver

    def _logged_in(self) -> bool:
        return not self.driver.find_elements(By.ID, "loginLink")

    def _wait(self) -> WebDriverWait:
        return WebDriverWait(self.driver, 10)


class LoginState(State):
    def login(self, username: str, password: str) -> PortalState:
        login(self._context.driver, username, password)
        return PortalState(self._context)


class PortalState(State):
    def electric(self) -> ElectricState:
        logger.info("Going to electric")
        self.driver.get("https://secure.rateacuity.com/RateAcuity/ElecEntry/IndexViews")
        return ElectricState(self._context)


class ElectricState(State):
    def benchmark(self) -> ElectricBenchmarkStateDropdown:
        self._select_report("benchmark")
        return ElectricBenchmarkStateDropdown(self._context)

    def _select_report(self, report: str):
        radio = self._wait().until(
            EC.presence_of_element_located((By.XPATH, f'//input[@id="report" and @value="{report}"]'))
        )
        if not radio.is_selected():
            radio.click()


class ElectricBenchmarkStateDropdown(State):
    def _wait_for_element(self):
        return self._wait().until(EC.presence_of_element_located((By.ID, "StateSelect")))

    def get_states(self) -> list[str]:
        dropdown = self._wait_for_element()
        options = dropdown.find_elements(By.TAG_NAME, "option")
        return [_.text for _ in options]

    def select_state(self, state: str) -> ElectricBenchmarkUtilityDropdown:
        dropdown = self._wait_for_element()
        options = [_.text.strip() for _ in dropdown.find_elements(By.TAG_NAME, "option")]
        if state not in options:
            raise ValueError(f"State {state} is invalid. Available options are: {options}")
        select = Select(dropdown)
        current = select.first_selected_option.text.strip() if select.first_selected_option else None
        if current != select:
            logger.info(f"Selecting state {state}")
            select.select_by_visible_text(state)
        return ElectricBenchmarkUtilityDropdown(self._context)


class ElectricBenchmarkUtilityDropdown(ElectricBenchmarkStateDropdown):
    def _wait_for_element(self):
        return self._wait().until(EC.presence_of_element_located((By.ID, "UtilitySelect")))

    def get_utilities(self) -> list[str]:
        dropdown = self._wait_for_element()
        options = dropdown.find_elements(By.TAG_NAME, "option")
        return [_.text for _ in options]

    def select_utility(self, utility: str):
        dropdown = self._wait_for_element()
        options = [_.text.strip() for _ in dropdown.find_elements(By.TAG_NAME, "option")]
        if utility not in options:
            raise ValueError(f"Utility {utility} is invalid. Available options are: {options}")
        select = Select(dropdown)
        current = select.first_selected_option.text.strip() if select.first_selected_option else None
        if current != select:
            logger.info(f"Selecting utility {utility}")
            select.select_by_visible_text(utility)
        return ElectricBenchmarkScheduleDropdown(self._context)


class ElectricBenchmarkScheduleDropdown(ElectricBenchmarkUtilityDropdown):
    def _wait_for_element(self):
        return self._wait().until(EC.presence_of_element_located((By.ID, "ScheduleSelect")))

    def get_schedules(self) -> list[str]:
        dropdown = self._wait_for_element()
        options = dropdown.find_elements(By.TAG_NAME, "option")
        return [_.text for _ in options]

    def select_schedule(self, schedule: str):
        dropdown = self._wait_for_element()
        options = [_.text.strip() for _ in dropdown.find_elements(By.TAG_NAME, "option")]
        if schedule not in options:
            raise ValueError(f"Schedule {schedule} is invalid. Available options are: {options}")
        select = Select(dropdown)
        current = select.first_selected_option.text.strip() if select.first_selected_option else None
        if current != select:
            logger.info(f"Selecting schedule {schedule}")
            select.select_by_visible_text(schedule)
        return ElectricBenchmarkReport(self._context)


class ElectricBenchmarkReport(State):
    def back_to_selections(self) -> ElectricBenchmarkScheduleDropdown:
        self._wait().until(EC.presence_of_element_located((By.LINK_TEXT, "Back To Selections"))).click()
        return ElectricBenchmarkScheduleDropdown(self._context)

    def download_excel(self) -> Path:
        self._wait().until(EC.presence_of_element_located((By.XPATH, '//a[text()="Create Excel Spreadsheet"]'))).click()
        download_path = self._context.download_path
        initial_state = _get_xlsx(download_path)

        n = 20
        while _get_xlsx(download_path) == initial_state and n:
            sleep(1)
            n -= 1

        filename = next(iter(_get_xlsx(download_path) ^ initial_state))
        print("Filename:", filename)
        return Path(download_path, filename)

    def as_dataframe(self) -> pl.DataFrame:
        filepath = self.download_excel()
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


def _get_xlsx(folder) -> set[str]:
    return {_ for _ in os.listdir(folder) if _.endswith(".xlsx")}


def main(argv: Sequence[str] | None = None):
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

        for schedule in filtered[:3]:
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
