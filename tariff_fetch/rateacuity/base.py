import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import NamedTuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


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


def login(driver: webdriver.Chrome, email_address: str, password: str):
    logger.info("Logging in")
    driver.get("https://secure.rateacuity.com/RateAcuityPortal/Account/Login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "UserName"))).send_keys(email_address)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(password)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Log in']"))
    ).click()
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
