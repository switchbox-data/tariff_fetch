import argparse
import datetime
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypedDict

from typing_extensions import Unpack

from .base import BASE_URL, api_request_json
from .converters import comma_separated, true_or_false
from .pagination import PagingParams, paging_params_converters

__all__ = [
    "TARIFFS_URL",
    "CustomerClass",
    "TariffType",
    "TariffsGetPageParams",
    "TariffsParams",
    "tariffs_get_page",
    "tariffs_paginate",
]

TARIFFS_URL = f"{BASE_URL}/tariffs"


CustomerClass: TypeAlias = Literal["RESIDENTIAL"] | Literal["GENERAL"] | Literal["SPECIAL_USE"]
TariffType: TypeAlias = Literal["DEFAULT"] | Literal["ALTERNATIVE"] | Literal["OPTIONAL_EXTRA"] | Literal["RIDER"]


class TariffsParams(TypedDict, total=False):
    lseId: int
    fields: Literal["min", "ext"]
    effectiveOn: datetime.date
    masterTariffId: int
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
    auth: tuple[str, str] | None = None,
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


def tariffs_get_page(auth: tuple[str, str] | None = None, **params: Unpack[TariffsGetPageParams]) -> dict[str, Any]:
    converters = {**_tariffs_params_converters, **paging_params_converters}
    request_params = {key: converters.get(key, lambda _: _)(value) for key, value in params.items()}
    return api_request_json(TARIFFS_URL, auth, **request_params)


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(description="Fetch Arcadia utility rates")
    parser.add_argument("lseid", help="Utility ID")
    parser.add_argument(
        "--appid",
        default=os.getenv("ARCADIA_APP_ID"),
        help="Arcadia App Id (defaults to ARCADIA_APP_ID environment variable)",
    )
    parser.add_argument(
        "--appkey",
        default=os.getenv("ARCADIA_APP_KEY"),
        help="Arcadia App Key (defaults to ARCADIA_APP_KEY environment variable)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="arcadia_utility_rates.json",
        help="Path to write the fetched rates (default: %(default)s).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    app_id = args.appid
    if not app_id:
        parser.error("App Id must be provided via --appid or ARCADIA_APP_ID environment variable")
    app_key = args.appkey
    if not app_key:
        parser.error("App Key must be provided via --appkey or ARCADIA_APP_KEY environment variable")

    tariffs = list(
        tariffs_paginate(
            (app_id, app_key),
            lseId=args.lseid,
            customerClasses=["RESIDENTIAL"],
            tariffTypes=["DEFAULT", "ALTERNATIVE", "OPTIONAL_EXTRA"],
            effectiveOn=datetime.datetime.now(datetime.timezone.utc),
            populateRates=True,
        )
    )
    output_path = Path(args.output)
    output_path.write_text(json.dumps(tariffs, indent=2))
    print(f"Wrote {len(tariffs)} records to {output_path}")


if __name__ == "__main__":
    main()
