import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from json import JSONDecodeError
from typing import Annotated, Any, Generic, Literal, Self, TypeVar, Unpack, overload
from urllib.parse import urljoin

import requests
from pydantic import ConfigDict, PlainSerializer, TypeAdapter
from pydantic.alias_generators import to_camel
from requests.auth import HTTPBasicAuth
from typing_extensions import TypedDict

from .schema.common import CustomerClass, TariffType
from .schema.lookup import Lookup
from .schema.lse import LSEExtended, LSEMinimal, ServiceType
from .schema.tariff import TariffExtended, TariffStandard

_BASE_URL = "https://api.genability.com/rest/public/"
_comma_separated = PlainSerializer(",".join)

_T = TypeVar("_T")
_C = TypeVar("_C")


class SearchParams(TypedDict, total=False):
    search: str
    """
    The string of text to search on.
    This can also be a regular expression, in which case you should
    set the isRegex flag to true (see below).
    """
    search_on: Annotated[list[str], _comma_separated]
    """
    Comma-separated list of fields to query on. When searchOn is specified, the text provided
    in the search string field will be searched within these fields. The list of fields to search on
    depends on the entity being searched for. Read the documentation for the entity for more details
    """
    starts_with: bool
    "When true, the search will only return results that begin with the specified search string."
    ends_with: bool
    "When true, the search will only return results that end with the specified search string."
    is_regex: bool
    """
    When true, the provided search string will be regarded as a regular expression
    and the search will return results matching the regular expression.
    Default is False.
    """
    sort_on: Annotated[list[str], _comma_separated]
    sort_order: Annotated[list[Literal["ASC", "DESC"]], _comma_separated]
    """
    Comma-separated list of ordering. Possible values are ASC and DESC. Default is ASC.
    If your sortOn contains multiple fields and you would like to order fields individually,
    you can pass in a comma-separated list here
    """


class PagingParams(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(alias_generator=to_camel)  # pyright: ignore[reportGeneralTypeIssues,reportUnannotatedClassAttribute]
    page_start: Annotated[int, PlainSerializer(str)]
    page_count: Annotated[int, PlainSerializer(str)]


class GetLSEsParams(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(alias_generator=to_camel)  # pyright: ignore[reportGeneralTypeIssues,reportUnannotatedClassAttribute]
    zip_code: str
    "Zip or post code where you would like to see a list of LSEs for (e.g. 5 digit ZIP code for USA)."
    country: str
    "ISO country code"
    ownerships: Annotated[list[Literal["INVESTOR", "COOP", "MUNI"]], _comma_separated]
    "Filter results by the type of ownership structure for the LSE."
    serviceTypes: Annotated[list[ServiceType], _comma_separated]
    "Filter results to LSEs that just offer this service type to a customer class"
    residential_service_types: Annotated[list[ServiceType], _comma_separated]
    commercial_service_types: Annotated[list[ServiceType], _comma_separated]
    industrial_service_types: Annotated[list[ServiceType], _comma_separated]
    transportation_service_types: Annotated[list[ServiceType], _comma_separated]


class TariffsParams(TypedDict, total=False):
    lse_id: int
    effective_on: date
    customer_classes: Annotated[list[CustomerClass], _comma_separated]
    master_tariff_id: int
    tariff_types: Annotated[list[TariffType], _comma_separated]
    populate_properties: bool
    populate_rates: bool
    populate_documents: bool
    from_date_time: date
    to_date_time: date


class LookupsParams(PagingParams, total=False):
    __pydantic_config__ = ConfigDict(alias_generator=to_camel)  # pyright: ignore[reportGeneralTypeIssues,reportUnannotatedClassAttribute]
    sub_property_key: str
    """Subproperty key name"""
    from_date_time: date
    to_date_time: date


class PropertyParams(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(alias_generator=to_camel)  # pyright: ignore[reportGeneralTypeIssues,reportUnannotatedClassAttribute]


class PageResponse(TypedDict, Generic[_T]):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    status: str
    count: int
    type: str
    results: list[_T]
    page_count: int
    page_start: int


class GetLSEsPageParams(PagingParams, SearchParams, GetLSEsParams):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class GetTariffsPageParams(PagingParams, SearchParams, TariffsParams):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


@dataclass(frozen=True)
class ArcadiaSignalAPIAuth:
    app_id: str
    app_key: str

    @classmethod
    def from_env(cls) -> Self:
        app_id = os.getenv("ARCADIA_APP_ID")
        if app_id is None:
            raise ValueError("ARCADIA_APP_ID variable is not set. Either set it or use auth as a parameter.")
        app_key = os.getenv("ARCADIA_APP_KEY")
        if app_key is None:
            raise ValueError("ARCADIA_APP_KEY variable is not set. Either set it or use auth as a parameter.")
        return cls(app_id, app_key)


@dataclass(frozen=True)
class ArcadiaSignalAPI:
    auth: ArcadiaSignalAPIAuth = field(default_factory=ArcadiaSignalAPIAuth.from_env)
    base_url: str = _BASE_URL
    session: requests.Session = field(default_factory=requests.Session)

    def _request(self, path: str, **params) -> dict[str, Any]:  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType, reportExplicitAny]
        response = self.session.get(
            urljoin(self.base_url, path),
            params=params,  # pyright: ignore[reportUnknownArgumentType]
            auth=HTTPBasicAuth(self.auth.app_id, self.auth.app_key),
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            if (message := _extract_arcadia_error_message(response)) is not None:
                raise requests.HTTPError(message, response=response, request=response.request) from e
            raise
        return response.json()  # pyright: ignore[reportAny]

    def _request_typed(
        self,
        path: str,
        params: _C,
        extras: dict[str, Any],  # pyright: ignore[reportExplicitAny]
        params_type: type[_C],
        response_type: type[_T],
    ) -> _T:
        param_type_adapter = TypeAdapter(params_type)
        params_to_api = param_type_adapter.dump_python(params, by_alias=True)  # pyright: ignore[reportAny]
        response = self._request(path, **params_to_api, **extras)  # pyright: ignore[reportUnknownMemberType, reportAny]
        result_adapter = TypeAdapter(response_type)
        return result_adapter.validate_python(response)

    @property
    def lses(self) -> "ArcadiaSignalAPILse":
        return ArcadiaSignalAPILse(self.auth, self.base_url, self.session)

    @property
    def tariffs(self) -> "ArcadiaSignalAPITariff":
        return ArcadiaSignalAPITariff(self.auth, self.base_url, self.session)

    @property
    def properties(self) -> "ArcadiaPropertiesAPI":
        return ArcadiaPropertiesAPI(self.auth, self.base_url, self.session)


@dataclass(frozen=True)
class ArcadiaSignalAPILse(ArcadiaSignalAPI):
    @overload
    def get_page(self, **params: Unpack[GetLSEsPageParams]) -> PageResponse[LSEMinimal]: ...

    @overload
    def get_page(self, fields: None, **params: Unpack[GetLSEsPageParams]) -> PageResponse[LSEMinimal]: ...

    @overload
    def get_page(self, fields: Literal["min"], **params: Unpack[GetLSEsPageParams]) -> PageResponse[LSEMinimal]: ...

    @overload
    def get_page(self, fields: Literal["ext"], **params: Unpack[GetLSEsPageParams]) -> PageResponse[LSEExtended]: ...

    def get_page(self, fields: Literal["min", "ext"] | None = None, **params: Unpack[GetLSEsPageParams]):
        match fields:
            case "min" | None:
                return self._request_typed(
                    "lses", params, {"fields": "min"}, GetLSEsPageParams, PageResponse[LSEMinimal]
                )
            case "ext":
                return self._request_typed(
                    "lses", params, {"fields": "ext"}, GetLSEsPageParams, PageResponse[LSEExtended]
                )


@dataclass(frozen=True)
class ArcadiaSignalAPITariff(ArcadiaSignalAPI):
    # @overload
    # def get_page(
    #    self, fields: Literal["min"], **params: Unpack[GetTariffsPageParams]
    # ) -> PageResponse[TariffMinimal]: ...

    @overload
    def get_page(
        self, fields: Literal["ext"], **params: Unpack[GetTariffsPageParams]
    ) -> PageResponse[TariffExtended]: ...

    @overload
    def get_page(self, fields: None, **params: Unpack[GetTariffsPageParams]) -> PageResponse[TariffStandard]: ...

    @overload
    def get_page(self, **params: Unpack[GetTariffsPageParams]) -> PageResponse[TariffStandard]: ...

    def get_page(self, fields: Literal["ext"] | None = None, **params: Unpack[GetTariffsPageParams]):
        match fields:
            # case "min":
            # return self._request_typed(
            #    "tariffs", params, {"fields": "min"}, GetTariffsPageParams, PageResponse[TariffMinimal]
            # )
            case "ext":
                return self._request_typed(
                    "tariffs", params, {"fields": "ext"}, GetTariffsPageParams, PageResponse[TariffExtended]
                )
            case None:
                return self._request_typed("tariffs", params, {}, GetTariffsPageParams, PageResponse[TariffStandard])

    # @overload
    # def iter_pages(self, fields: Literal["min"], **params: Unpack[GetTariffsPageParams]) -> Iterator[TariffMinimal]: ...

    @overload
    def iter_pages(
        self, fields: Literal["ext"], **params: Unpack[GetTariffsPageParams]
    ) -> Iterator[TariffExtended]: ...

    @overload
    def iter_pages(self, fields: None, **params: Unpack[GetTariffsPageParams]) -> Iterator[TariffStandard]: ...

    @overload
    def iter_pages(self, **params: Unpack[GetTariffsPageParams]) -> Iterator[TariffStandard]: ...

    def iter_pages(
        self, fields: Literal["ext"] | None = None, **params: Unpack[GetTariffsPageParams]
    ) -> Iterator[TariffExtended] | Iterator[TariffStandard]:
        page_start = params.get("page_start", 0)
        while True:
            params_: GetTariffsPageParams = {**params, "page_start": page_start}
            response = self.get_page(fields, **params_)
            count, page_start = response["count"], response["page_start"]
            size = len(response["results"])
            yield from response["results"]  # pyright: ignore[reportReturnType]
            if page_start + size >= count:
                return
            if size <= 0:
                return
            page_start += size


@dataclass(frozen=True)
class ArcadiaPropertiesAPI(ArcadiaSignalAPI):
    @property
    def lookups(self) -> "ArcadiaLookupsAPI":
        return ArcadiaLookupsAPI(self.auth, self.base_url, self.session)


@dataclass(frozen=True)
class ArcadiaLookupsAPI(ArcadiaPropertiesAPI):
    def get_page(self, property_key: str, **params: Unpack[LookupsParams]) -> PageResponse[Lookup]:
        return self._request_typed(
            f"properties/{property_key}/lookups", params, {}, LookupsParams, PageResponse[Lookup]
        )

    def iter_pages(self, property_key: str, **params: Unpack[LookupsParams]) -> Iterator[Lookup]:
        page_start = params.get("page_start", 0)
        while True:
            params_: LookupsParams = {**params, "page_start": page_start}
            response = self.get_page(property_key, **params_)
            count, page_start = response["count"], response["page_start"]
            size = len(response["results"])
            yield from response["results"]
            if page_start + size >= count:
                return
            if size <= 0:
                return
            page_start += size


def _extract_arcadia_error_message(response: requests.Response) -> str | None:
    try:
        payload = response.json()  # pyright: ignore[reportAny]
    except (JSONDecodeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None

    results = payload.get("results")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if not isinstance(results, list):
        return None

    messages = [  # pyright: ignore[reportUnknownVariableType]
        item["message"]
        for item in results  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, dict) and isinstance(item.get("message"), str) and item["message"].strip()  # pyright: ignore[reportUnknownMemberType]
    ]
    if not messages:
        return None

    return "; ".join(messages)  # pyright: ignore[reportUnknownArgumentType]
