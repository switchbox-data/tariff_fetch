import os
from typing import Literal, TypeAlias, TypedDict, Unpack

from tariff_fetch.genability.converters import comma_separated
from tariff_fetch.genability.pagination import PagingParams, paging_params_converters
from tariff_fetch.genability.search import SearchParams, search_params_converters

from .base import BASE_URL, api_request_json

LSE_URL = f"{BASE_URL}/lses"

LSEServiceType: TypeAlias = Literal["ELECTRICITY", "SOLAR_PV"]


class GetLSEsParams(TypedDict, total=False):
    fields: str
    zipCode: str
    "Zip or post code where you would like to see a list of LSEs for (e.g. 5 digit ZIP code for USA)."
    country: str
    "ISO country code"
    ownerships: list[Literal["INVESTOR", "COOP", "MUNI"]]
    "Filter results by the type of ownership structure for the LSE."
    serviceTypes: list[LSEServiceType]
    "Filter results to LSEs that just offer this service type to a customer class"
    residentialServiceTypes: list[LSEServiceType]
    commercialServiceTypes: list[LSEServiceType]
    industrialServiceTypes: list[LSEServiceType]
    transportationServiceTypes: list[LSEServiceType]


_get_lses_params_converters = {
    "ownerships": comma_separated,
    "serviceTypes": comma_separated,
    "residentialServiceTypes": comma_separated,
    "commercialServiceTypes": comma_separated,
    "industrialServiceTypes": comma_separated,
    "transportationServiceTypes": comma_separated,
}


class GetLSEsPageParams(PagingParams, SearchParams, GetLSEsParams): ...


def ident(x):
    return x


def get_lses_page(
    auth: tuple[str, str] | None = None,
    **params: Unpack[GetLSEsPageParams],
):
    converters = {**_get_lses_params_converters, **paging_params_converters, **search_params_converters}
    request_params = {key: converters.get(key, ident)(value) for key, value in params.items()}
    return api_request_json(LSE_URL, auth=auth, **request_params)


def main():
    from dotenv import load_dotenv

    load_dotenv()
    app_id = os.getenv("ARCADIA_APP_ID")
    app_key = os.getenv("ARCADIA_APP_KEY")
    if not (app_id and app_key):
        raise ValueError("Provide app id and key")
    result = get_lses_page((app_id, app_key), fields="min", search="4226", searchOn=["code"])
    print(result)


if __name__ == "__main__":
    main()
