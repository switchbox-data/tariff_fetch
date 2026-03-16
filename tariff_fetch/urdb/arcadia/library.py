"""Arcadia data access, caching, prompting, and debug persistence for conversion."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Literal, final, overload

from requests import HTTPError

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.lookup import Lookup
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyPrunedDataType, TariffPropertyStandard
from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.arcadia.exception import TariffAccessDenied, TariffNotFoundByDate, TariffNotFoundById

from .exception import ConversionError
from .prompts import (
    prompt_boolean,
    prompt_choice,
    prompt_date,
    prompt_decimal,
    prompt_demand,
    prompt_integer,
    prompt_string,
)
from .shared import as_naive_datetime

PropertyValue = str | list[str] | bool | date | float | int
_DEFAULT_DEBUG_ROOT = Path("./outputs/arcadia_library")


def _json_default(value: object) -> str:
    """Serialize date-like values used in debug JSON dumps."""

    if isinstance(value, datetime | date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


@final
class LibraryDebugStore:
    """Persist fetched Arcadia artifacts to disk for debugging."""

    def __init__(self, root: Path = _DEFAULT_DEBUG_ROOT) -> None:
        self.root = root
        self.tariffs_dir = root / "tariffs"
        self.lookups_dir = root / "lookups"
        self.properties_dir = root / "properties"

    def save_tariff(self, tariff: TariffExtended) -> None:
        """Write one fetched tariff version to the debug output folder."""

        effective_date = tariff["effective_date"].isoformat()
        tariff_id = tariff["tariff_id"]
        master_tariff_id = tariff["master_tariff_id"]
        path = self.tariffs_dir / f"master-{master_tariff_id}_tariff-{tariff_id}_effective-{effective_date}.json"
        self._write_json(path, tariff)

    def save_lookups(self, key: str, year: int, lookups: list[Lookup]) -> None:
        """Write one variable lookup timeseries to the debug output folder."""

        path = self.lookups_dir / f"{key}_{year}.json"
        self._write_json(path, lookups)

    def save_property_value(self, key: str, value: PropertyValue) -> None:
        """Write one prompted property value to the debug output folder."""

        path = self.properties_dir / f"{key}.json"
        self._write_json(path, {"key": key, "value": value})

    def _write_json(self, path: Path, payload: object) -> None:
        """Create the target directory and write formatted JSON payload."""

        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(json.dumps(payload, indent=2, default=_json_default))


@final
class TariffLibrary:
    """Fetch and cache Arcadia tariff versions and related tariff metadata."""

    def __init__(self, api: ArcadiaSignalAPI, debug_store: LibraryDebugStore) -> None:
        self.api = api
        self.debug_store = debug_store
        self.tariffs: list[TariffExtended] = []
        self._access_denied_tariff_ids: set[int] = set()

    def get_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended:
        """Return the tariff version effective for a master tariff on a given date."""

        dt = dt.date() if isinstance(dt, datetime) else dt
        if (found := self._find_tariff_at_date(master_tariff_id, dt)) is not None:
            return found
        tariff = self._fetch_tariff_at_date(master_tariff_id, dt)
        self._remember(tariff)
        return tariff

    def get_tariff(self, tariff_id: int) -> TariffExtended:
        """Return a tariff by version-specific Arcadia tariff id."""

        if (found := self._find_tariff(tariff_id)) is not None:
            return found
        if tariff_id in self._access_denied_tariff_ids:
            raise TariffAccessDenied(tariff_id)
        tariff = self._fetch_tariff(tariff_id)
        self._remember(tariff)
        return tariff

    def get_rate(self, rate_id: int) -> TariffRateExtended:
        """Return a cached rate by Arcadia tariff rate id."""

        return next(
            rate for tariff in self.tariffs for rate in tariff.get("rates", []) if rate["tariff_rate_id"] == rate_id
        )

    def get_property(self, key: str) -> TariffPropertyStandard:
        """Return a cached Arcadia tariff property definition by key name."""

        return next(prop for tariff in self.tariffs for prop in tariff.get("properties", []) if prop["key_name"] == key)

    def _find_tariff(self, tariff_id: int) -> TariffExtended | None:
        """Search the in-memory tariff cache by tariff id."""

        return next((t for t in self.tariffs if t["tariff_id"] == tariff_id), None)

    def _find_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended | None:
        """Search the in-memory cache for the tariff version effective on a given date."""

        for tariff in self.tariffs:
            if tariff["master_tariff_id"] != master_tariff_id:
                continue
            if _is_tariff_effective_on(tariff, dt):
                return tariff
        return None

    def _remember(self, tariff: TariffExtended) -> None:
        """Add a fetched tariff to the cache and write its debug dump."""

        self.tariffs.append(tariff)
        self.debug_store.save_tariff(tariff)

    def _fetch_tariff(self, tariff_id: int) -> TariffExtended:
        """Fetch one tariff version from Arcadia by tariff id."""

        try:
            tariffs = list(
                self.api.tariffs.iter_pages(
                    fields="ext",
                    search=str(tariff_id),
                    search_on=["tariffId"],
                    starts_with=True,
                    ends_with=True,
                    populate_properties=True,
                    populate_rates=True,
                )
            )
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                self._access_denied_tariff_ids.add(tariff_id)
                raise TariffAccessDenied(tariff_id) from e
            raise
        if len(tariffs) > 1:
            raise RuntimeError(f"More than one tariff found for id={tariff_id}")
        if not tariffs:
            raise TariffNotFoundById(tariff_id)
        return tariffs[0]

    def _fetch_tariff_at_date(self, master_tariff_id: int, dt: date) -> TariffExtended:
        """Fetch the tariff version effective for a master tariff on a given date."""

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
    """Fetch and cache Arcadia variable lookup timeseries by property key and year."""

    def __init__(self, api: ArcadiaSignalAPI, debug_store: LibraryDebugStore):
        self.api = api
        self.debug_store = debug_store
        self.property_timeseries: dict[tuple[str, int], list[Lookup]] = {}

    def lookup(self, key: str, dt: datetime) -> float:
        """Return the best available lookup value for a property at a datetime."""

        if (lookups := self.property_timeseries.get((key, dt.year))) is None:
            lookups = self._lookup_property_timeseries(key, dt.year)
            self.property_timeseries[(key, dt.year)] = lookups
            self.debug_store.save_lookups(key, dt.year, lookups)

        for row in lookups:
            if (
                as_naive_datetime(row["from_date_time"])
                <= as_naive_datetime(dt)
                <= as_naive_datetime(row["to_date_time"] or datetime.max)
            ):
                if (value := row["actual_value"]) is not None:
                    return value
                if (value := row["best_value"]) is not None:
                    return value
                if (value := row["forecast_value"]) is not None:
                    return value
                return 0.0
        return 0.0

    def _lookup_property_timeseries(self, key: str, year: int) -> list[Lookup]:
        """Fetch one year of lookup rows for a variable Arcadia property."""

        return list(
            self.api.properties.lookups.iter_pages(
                key,
                from_date_time=date(year, 1, 1),
                to_date_time=date(year + 1, 1, 1),
            )
        )


@final
class Library:
    """Top-level Arcadia conversion helper for tariffs, lookups, and prompted properties."""

    def __init__(
        self,
        api: ArcadiaSignalAPI,
        properties: dict[str, PropertyValue] | None = None,
        debug_root: Path = _DEFAULT_DEBUG_ROOT,
    ):
        self.api = api
        self.debug_store = LibraryDebugStore(debug_root)
        self.tariffs = TariffLibrary(api, self.debug_store)
        self.variables = VariablePropertyLibrary(api, self.debug_store)
        self._properies: dict[str, PropertyValue] = properties or {}
        self._issues: dict[tuple[object, ...], str] = {}

    def has_property(self, key: str) -> bool:
        """Return whether a property value has already been supplied or cached."""

        return key in self._properies

    def record_issue(self, key: tuple[object, ...], message: str) -> None:
        """Record a deduplicated conversion issue for this conversion run."""

        _ = self._issues.setdefault(key, message)

    def iter_issues(self) -> list[str]:
        """Return the unique conversion issues recorded during this conversion run."""

        return list(self._issues.values())

    def get_choice_property_as_ints(self, key: str) -> list[int]:
        """Return a CHOICE property as integer ids."""

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
        """Return a property value, prompting and caching it if needed."""

        if (found := self._get_property(key, data_type)) is not None:
            return found
        tariff_property = self.tariffs.get_property(key)
        result = _prompt_property(tariff_property)
        if result is None:
            raise ConversionError("Property not set")
        self._properies[key] = result
        self.debug_store.save_property_value(key, result)
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
        """Return a cached property value after validating its expected data type."""

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
                if not isinstance(value, int):
                    raise ConversionError(f"Value for property {key} is expected to be `int`, not {value_type}")
                return value

            case "DEMAND":
                if not isinstance(value, float):
                    raise ConversionError(f"Value for property {key} is expected to be `float`, not {value_type}")
                return value


def _is_tariff_effective_on(tariff: TariffExtended, dt: date) -> bool:
    """Return whether a tariff version is effective on the given date."""

    effective_date = tariff["effective_date"]
    end_date = tariff["end_date"] or date.max
    return effective_date <= dt < end_date


def _prompt_property(tariff_property: TariffPropertyStandard) -> PropertyValue | None:
    """Prompt the user for a property value using the Arcadia property data type."""

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
