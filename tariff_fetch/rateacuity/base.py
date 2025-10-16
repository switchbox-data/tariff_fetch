import os
from collections.abc import Generator
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from time import sleep
from typing import NamedTuple

import polars as pl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

DOWNLOAD_PATH = os.path.join(os.getcwd(), "outputs")


class ScrapingContext(NamedTuple):
    driver: webdriver.Chrome
    download_path: str


@contextmanager
def create_context() -> Generator[ScrapingContext]:
    with TemporaryDirectory() as temp_dir:
        yield ScrapingContext(create_driver_(temp_dir), temp_dir)


def create_driver_(download_path: str) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
    )
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_path,
            "download.prompt_for_download": False,
            "directory_upgrade": True,
        },
    )
    service = Service(log_path=os.devnull)
    return webdriver.Chrome(options=options, service=service)


def get_electric_tariffs(context: ScrapingContext, state: str, utility: str, schedule: str) -> pl.DataFrame:
    driver, _ = context
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.get("https://secure.rateacuity.com/RateAcuity/ElecEntry/IndexViews")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@id='report' and @value='benchmark']"))
    ).click()

    select_state(driver, state)
    select_utility(driver, utility)
    select_schedule(driver, schedule)

    filepath = download_excel(context)

    result = read_excel(filepath)

    # remove downloaded excel file
    os.unlink(filepath)
    return result


def read_excel(filepath: str):
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
    select.select_by_visible_text(state)


def select_utility(driver: webdriver.Chrome, utility: str):
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UtilitySelect")))
    options = dropdown.find_elements(By.TAG_NAME, "option")
    option_texts = [_.text.strip() for _ in options]
    if utility not in option_texts:
        raise ValueError(f"Utility {utility} is invalid. Available options are: {option_texts}")
    select = Select(dropdown)
    select.select_by_visible_text(utility)


def select_schedule(driver: webdriver.Chrome, schedule: str):
    dropdown = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ScheduleSelect")))
    options = dropdown.find_elements(By.TAG_NAME, "option")
    option_texts = [_.text.strip() for _ in options]
    if schedule not in option_texts:
        raise ValueError(f"Schedule {schedule} is invalid. Available options are: {option_texts}")
    select = Select(dropdown)
    select.select_by_visible_text(schedule)


def login(driver: webdriver.Chrome, email_address: str, password: str):
    driver.get("https://secure.rateacuity.com/RateAcuityPortal/Account/Login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UserName"))).send_keys(email_address)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(password)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Log in']"))
    ).click()
