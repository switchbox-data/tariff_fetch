from datetime import date, datetime
from typing import Literal, final, overload
from xdrlib import ConversionError

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.lookup import Lookup
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyPrunedDataType, TariffPropertyStandard
from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.arcadia.exception import TariffNotFoundByDate, TariffNotFoundById

from .prompts import (
    prompt_boolean,
    prompt_choice,
    prompt_date,
    prompt_decimal,
    prompt_demand,
    prompt_integer,
    prompt_string,
)

PropertyValue = str | list[str] | bool | date | float | int


@final
class TariffLibrary:
    def __init__(self, api: ArcadiaSignalAPI) -> None:
        self.api = api
        self.tariffs: list[TariffExtended] = []

    def get_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended:
        dt = dt.date() if isinstance(dt, datetime) else dt
        if (found := self._find_tariff_at_date(master_tariff_id, dt)) is not None:
            return found
        tariff = self._fetch_tariff_at_date(master_tariff_id, dt)
        self.tariffs.append(tariff)
        return tariff

    def get_tariff(self, tariff_id: int) -> TariffExtended:
        if (found := self._find_tariff(tariff_id)) is not None:
            return found
        tariff = self._fetch_tariff(tariff_id)
        self.tariffs.append(tariff)
        return tariff

    def get_rate(self, rate_id: int) -> TariffRateExtended:
        return next(
            rate for tariff in self.tariffs for rate in tariff.get("rates", []) if rate["tariff_rate_id"] == rate_id
        )

    def get_property(self, key: str) -> TariffPropertyStandard:
        return next(prop for tariff in self.tariffs for prop in tariff.get("properties", []) if prop["key_name"] == key)

    def _find_tariff(self, tariff_id: int) -> TariffExtended | None:
        return next((t for t in self.tariffs if t["tariff_id"] == tariff_id), None)

    def _find_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended | None:
        for tariff in self.tariffs:
            if tariff["master_tariff_id"] != master_tariff_id:
                continue
            if _is_tariff_effective_on(tariff, dt):
                return tariff
        return None

    def _fetch_tariff(self, tariff_id: int) -> TariffExtended:
        tariffs = list(
            self.api.tariffs.iter_pages(
                fields="ext",
                search=str(tariff_id),
                search_on=["tariffId"],
                populate_properties=True,
                populate_rates=True,
            )
        )
        if len(tariffs) > 1:
            raise RuntimeError(f"More than one tariff found for id={tariff_id}")
        if not tariffs:
            raise TariffNotFoundById(tariff_id)
        return tariffs[0]

    def _fetch_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended:
        tariffs = self.api.tariffs.iter_pages(
            fields="ext",
            master_tariff_id=master_tariff_id,
            effective_on=(dt.date() if isinstance(dt, datetime) else dt),
            populate_properties=True,
            populate_rates=True,
        )
        try:
            return next(t for t in tariffs if _is_tariff_effective_on(t, dt))
        except StopIteration as e:
            raise TariffNotFoundByDate(master_tariff_id, dt) from e


@final
class VariablePropertyLibrary:
    def __init__(self, api: ArcadiaSignalAPI):
        self.api = api
        self.property_timeseries: dict[tuple[str, int], list[Lookup]] = {}

    def lookup(self, key: str, dt: datetime) -> float:
        if (lookups := self.property_timeseries.get((key, dt.year))) is None:
            lookups = self._lookup_property_timeseries(key, dt.year)
            self.property_timeseries[(key, dt.year)] = lookups

        for row in lookups:
            if row["from_date_time"] <= dt <= (row["to_date_time"] or datetime.max):
                if (value := row["actual_value"]) is not None:
                    return value
                if (value := row["best_value"]) is not None:
                    return value
                if (value := row["forecast_value"]) is not None:
                    return value
                return 0.0
        return 0.0

    def _lookup_property_timeseries(self, key: str, year: int) -> list[Lookup]:
        return list(
            self.api.properties.lookups.iter_pages(
                key,
                from_date_time=date(year, 1, 1),
                to_date_time=date(year + 1, 1, 1),
            )
        )


@final
class Library:
    def __init__(self, api: ArcadiaSignalAPI, properties: dict[str, PropertyValue] | None = None):
        self.api = api
        self.tariffs = TariffLibrary(api)
        self.variables = VariablePropertyLibrary(api)
        self._properies: dict[str, PropertyValue] = properties or {}

    def has_property(self, key: str) -> bool:
        return key in self._properies

    def get_choice_property_as_ints(self, key: str) -> list[int]:
        strs = self.get_property(key, "CHOICE")
        try:
            return list(map(int, strs))
        except ValueError as e:
            raise ConversionError(f"Could not convert value of choice property {key} to strings") from e

    @overload
    def get_property(self, key: str, data_type: Literal["STRING"]) -> str: ...

    @overload
    def get_property(self, key: str, data_type: Literal["CHOICE"]) -> list[str]: ...

    @overload
    def get_property(self, key: str, data_type: Literal["BOOLEAN"]) -> bool: ...
    @overload
    def get_property(self, key: str, data_type: Literal["DATE"]) -> date: ...
    @overload
    def get_property(self, key: str, data_type: Literal["DECIMAL"]) -> float: ...
    @overload
    def get_property(self, key: str, data_type: Literal["INTEGER"]) -> int: ...
    @overload
    def get_property(self, key: str, data_type: Literal["DEMAND"]) -> float: ...

    def get_property(self, key: str, data_type: TariffPropertyPrunedDataType) -> PropertyValue:
        if (found := self._get_property(key, data_type)) is not None:
            return found
        tariff_property = self.tariffs.get_property(key)
        result = _prompt_property(tariff_property)
        if result is None:
            raise ConversionError("Property not set")
        self._properies[key] = result
        return result

    @overload
    def _get_property(self, key: str, data_type: Literal["STRING"]) -> str | None: ...

    @overload
    def _get_property(self, key: str, data_type: Literal["CHOICE"]) -> list[str] | None: ...

    @overload
    def _get_property(self, key: str, data_type: Literal["BOOLEAN"]) -> bool | None: ...
    @overload
    def _get_property(self, key: str, data_type: Literal["DATE"]) -> date | None: ...
    @overload
    def _get_property(self, key: str, data_type: Literal["DECIMAL"]) -> float | None: ...
    @overload
    def _get_property(self, key: str, data_type: Literal["INTEGER"]) -> int | None: ...
    @overload
    def _get_property(self, key: str, data_type: Literal["DEMAND"]) -> float | None: ...

    def _get_property(self, key: str, data_type: TariffPropertyPrunedDataType) -> PropertyValue | None:
        try:
            value = self._properies[key]
        except KeyError:
            return None
        value_type = type(value)
        match data_type:
            case "STRING":
                if not isinstance(value, str):
                    raise ConversionError(f"Value for property {key} is expected to be `str`, not {value_type}")
                return value
            case "CHOICE":
                if not isinstance(value, list):
                    raise ConversionError(f"Value for property {key} is expected to be a list, not {value_type}")
                return value
            case "BOOLEAN":
                if not isinstance(value, bool):
                    raise ConversionError(f"Value for property {key} is expected to be `bool`, not {value_type}")
                return value
            case "DATE":
                if not isinstance(value, date):
                    raise ConversionError(f"Value for property {key} is expected to be `bool`, not {value_type}")
                return value
            case "DECIMAL":
                if not isinstance(value, float):
                    raise ConversionError(f"Value for property {key} is expected to be `float`, not {value_type}")
                return value
            case "INTEGER":
                if not isinstance(value, bool):
                    raise ConversionError(f"Value for property {key} is expected to be `int`, not {value_type}")
                return value

            case "DEMAND":
                if not isinstance(value, bool):
                    raise ConversionError(f"Value for property {key} is expected to be `float`, not {value_type}")
                return value


def _is_tariff_effective_on(tariff: TariffExtended, dt: date) -> bool:
    effective_date = tariff["effective_date"]
    end_date = tariff["end_date"] or date.max
    return effective_date <= dt < end_date


def _prompt_property(tariff_property: TariffPropertyStandard) -> PropertyValue | None:
    data_type = tariff_property["data_type"]
    match data_type:
        case "BOOLEAN":
            return prompt_boolean(tariff_property)
        case "CHOICE":
            return prompt_choice(tariff_property)
        case "STRING":
            return prompt_string(tariff_property)
        case "DATE":
            return prompt_date(tariff_property)
        case "DECIMAL":
            return prompt_decimal(tariff_property)
        case "INTEGER":
            return prompt_integer(tariff_property)
        case "DEMAND":
            return prompt_demand(tariff_property)
        case "FORMULA":
            raise ValueError("Formula properties are not supported")
