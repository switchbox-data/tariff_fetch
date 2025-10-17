import argparse
import logging
import os
from collections.abc import Iterable, Sequence
from pathlib import Path
from time import sleep
from typing import NamedTuple

import polars as pl
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .base import ScrapingContext

logger = logging.getLogger(__name__)


class TariffFilter(NamedTuple):
    state: str
    utility: str
    schedule: str


def get_electric_tariffs(context: ScrapingContext, filters: Iterable[TariffFilter]) -> pl.DataFrame:
    driver, _ = context
    driver.get("https://secure.rateacuity.com/RateAcuity/ElecEntry/IndexViews")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@id='report' and @value='benchmark']"))
    ).click()

    frames: list[pl.DataFrame] = []

    for filter in filters:
        state, utility, schedule = filter

        back_to_selections_if_present(driver)

        select_state(driver, state)
        select_utility(driver, utility)
        select_schedule(driver, schedule)

        filepath = download_excel(context)

        df = read_excel(filepath)
        df = df.with_columns(pl.lit(schedule).alias("Schedule"))
        df = df.select(["Schedule", *[name for name in df.columns if name != "Schedule"]])
        frames.append(df)

        # remove downloaded excel file
        os.unlink(filepath)

    if not frames:
        return pl.DataFrame()

    return pl.concat(frames, how="vertical_relaxed", rechunk=True)


def back_to_selections_if_present(driver):
    back_to_selections = driver.find_elements(By.LINK_TEXT, "Back To Selections")
    if back_to_selections:
        logger.info("Clicking 'back to selections'")
        back_to_selections[0].click()


def read_excel(filepath: str):
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
    return df


def download_excel(context: ScrapingContext) -> str:
    logger.info("Downloading excel file")
    driver, download_path = context
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//a[text()="Create Excel Spreadsheet"]'))
    ).click()

    initial_state = _get_xlsx(download_path)

    n = 20
    while _get_xlsx(download_path) == initial_state and n:
        sleep(1)
        n -= 1

    filename = next(iter(_get_xlsx(download_path) ^ initial_state))
    print("Filename:", filename)
    return os.path.join(download_path, filename)


def _get_xlsx(folder) -> set[str]:
    return {_ for _ in os.listdir(folder) if _.endswith(".xlsx")}


def select_state(driver: webdriver.Chrome, state: str):
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "StateSelect")))
    options = dropdown.find_elements(By.TAG_NAME, "option")
    option_texts = [_.text.strip() for _ in options]
    if state not in option_texts:
        raise ValueError(f"State {state} is invalid. Available options are: {option_texts}")
    select = Select(dropdown)
    current = select.first_selected_option.text.strip() if select.first_selected_option else None
    if current != state:
        logger.info(f"Selecting state {state}")
        select.select_by_visible_text(state)


def select_utility(driver: webdriver.Chrome, utility: str):
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UtilitySelect")))
    options = dropdown.find_elements(By.TAG_NAME, "option")
    option_texts = [_.text.strip() for _ in options]
    if utility not in option_texts:
        raise ValueError(f"Utility {utility} is invalid. Available options are: {option_texts}")
    select = Select(dropdown)
    current = select.first_selected_option.text.strip() if select.first_selected_option else None
    if current != utility:
        logger.info(f"Selecting utility {utility}")
        select.select_by_visible_text(utility)


def select_schedule(driver: webdriver.Chrome, schedule: str):
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ScheduleSelect")))
    options = dropdown.find_elements(By.TAG_NAME, "option")
    option_texts = [_.text.strip() for _ in options]
    if schedule not in option_texts:
        raise ValueError(f"Schedule {schedule} is invalid. Available options are: {option_texts}")
    select = Select(dropdown)
    current = select.first_selected_option.text.strip() if select.first_selected_option else None
    if current != schedule:
        logger.info(f"Selecting schedule {schedule}")
        select.select_by_visible_text(schedule)


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

    from .base import create_context, login

    UTILITY = "Consolidated Edison Company of New York"
    STATE = "NY"

    with create_context() as context:
        login(context.driver, username, password)
        driver, _ = context
        driver.get("https://secure.rateacuity.com/RateAcuity/ElecEntry/IndexViews")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@id='report' and @value='benchmark']"))
        ).click()
        select_state(driver, STATE)
        select_utility(driver, UTILITY)
        try:
            dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ScheduleSelect")))
        finally:
            driver.save_screenshot("screenshot.png")
        options = dropdown.find_elements(By.TAG_NAME, "option")
        option_texts = [_.text.strip() for _ in options]
        schedules = [_ for _ in option_texts if "residential" in _.lower()]

        filters = [TariffFilter(STATE, UTILITY, schedule) for schedule in schedules]
        print(filters)

        output_path = Path(args.output)
        df = get_electric_tariffs(context, filters)
        df.write_csv(output_path)
        print(f"Wrote to {output_path}")


if __name__ == "__main__":
    main()
