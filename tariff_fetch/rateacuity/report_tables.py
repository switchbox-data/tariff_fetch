from __future__ import annotations

from typing import TypedDict

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement


class TableJson(TypedDict):
    title: str
    columns: list[str]
    values: list[dict[str, str]]


class SectionJson(TypedDict):
    section: str
    tables: list[TableJson]


def _headers_from_table(table: WebElement) -> list[str]:
    ths = table.find_elements(By.CSS_SELECTOR, "thead th")
    result = []
    for th in ths:
        links = th.find_elements(By.TAG_NAME, "a")
        result.append(links[0].text if links else th.text)
    return result


def _rows_from_table(table: WebElement) -> list[str]:
    rows = []
    for tr in table.find_elements(By.CSS_SELECTOR, "tbody tr"):
        tds = tr.find_elements(By.TAG_NAME, "td")
        rows.append([td.text for td in tds])
    return rows


def _table_json(table: WebElement) -> TableJson | None:
    columns = _headers_from_table(table)
    if not columns:
        return None
    rows = _rows_from_table(table)
    title = columns[0]

    values = []

    for row in rows:
        v = {}
        for c, r in zip(columns, row, strict=False):
            v[c] = r
        values.append(v)

    return TableJson(
        {
            "title": title,
            "columns": columns,
            "values": values,
        }
    )


def sections_to_json(driver: WebDriver) -> list[SectionJson]:
    seq = driver.find_elements(By.CSS_SELECTOR, "h3, table.eamwebgrid-table")

    sections = []
    current = {"section": None, "tables": []}
    for el in seq:
        tag = el.tag_name.lower()
        if tag == "h3":
            if current["section"] is not None or current["tables"]:
                sections.append(current)
            current = {"section": el.text, "tables": []}
        else:
            table = _table_json(el)
            if table:
                current["tables"].append(table)

    if current["section"] is not None or current["tables"]:
        sections.append(current)

    return sections
