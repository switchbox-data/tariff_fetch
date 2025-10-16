import datetime
from typing import Any, Literal, TypeAlias, TypedDict

from typing_extensions import Unpack

from .base import BASE_URL, api_request_json
from .converters import comma_separated, true_or_false
from .pagination import PagingParams, paging_params_converters

TARIFFS_URL = f"{BASE_URL}/tariffs"

CustomerClass: TypeAlias = Literal["RESIDENTIAL"] | Literal["GENERAL"] | Literal["SPECIAL_USE"]
TariffType: TypeAlias = Literal["DEFAULT"] | Literal["ALTERNATIVE"] | Literal["OPTIONAL_EXTRA"] | Literal["RIDER"]


class TariffsParams(TypedDict, total=False):
    lseId: int
    effectiveOn: datetime.date
    customerClasses: list[CustomerClass]
    tariffTypes: list[TariffType]
    populateProperties: bool
    populateRates: bool
    populateDocuments: bool


_tariffs_params_converters = {
    "effectiveOn": lambda _: _.strftime("%Y-%m-%d"),
    "customerClasses": comma_separated,
    "lseId": str,
    "populateProperties": true_or_false,
    "populateRates": true_or_false,
    "populateDocuments": true_or_false,
    "pageStart": str,
    "pageCount": str,
    "tariffTypes": comma_separated,
}


class TariffsGetPageParams(PagingParams, TariffsParams):
    pass


def tariffs_paginate(
    auth: tuple[str, str],
    start: int = 0,
    page_count: int = 25,
    **params: Unpack[TariffsParams],
):
    offset = start
    rows = page_count
    while rows >= page_count:
        page = tariffs_get_page(auth, **params, pageStart=offset, pageCount=page_count)
        rows = len(page["results"])
        offset += rows
        yield from page["results"]


def tariffs_get_page(auth: tuple[str, str], **params: Unpack[TariffsGetPageParams]) -> dict[str, Any]:
    converters = {**_tariffs_params_converters, **paging_params_converters}
    request_params = {key: converters[key](value) for key, value in params.items()}
    return api_request_json(TARIFFS_URL, auth, request_params)
