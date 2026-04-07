from collections.abc import Iterator
from datetime import datetime, timedelta
from math import inf

from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyStandard
from tariff_fetch.arcadia.schema.tariffrate import TariffRateBand, TariffRateExtended
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.schema import DemandTier, URDBRate

from . import rateutils as ru
from .library import Library
from .scenario import Scenario
from .shared import (
    average_aligned_bands,
    is_weekday,
    is_weekend,
    iter_sampled_datetimes,
    iter_year,
    sum_piecewise_bands,
)
from .types import Band, BandSet, DayPredicate

_SUPPORTED_QUANTITY_KEY = "kW"


def build_demand_schedule(scenario: Scenario, library: Library) -> URDBRate:
    weekday_schedule_raw = [
        [get_month_hour_bands(scenario, library, month, hour, is_weekday) for hour in range(24)]
        for month in range(1, 13)
    ]
    weekend_schedule_raw = [
        [get_month_hour_bands(scenario, library, month, hour, is_weekend) for hour in range(24)]
        for month in range(1, 13)
    ]

    # Order-preserving unique band sets
    band_sets: list[tuple[Band, ...]] = []
    band_index: dict[tuple[Band, ...], int] = {}

    for schedule in (weekday_schedule_raw, weekend_schedule_raw):
        for month in schedule:
            for bands in month:
                key = tuple(bands)
                if key not in band_index:
                    band_index[key] = len(band_sets)
                    band_sets.append(key)

    demand_weekday_schedule = tuple(tuple(band_index[tuple(hour)] for hour in month) for month in weekday_schedule_raw)
    demand_weekend_schedule = tuple(tuple(band_index[tuple(hour)] for hour in month) for month in weekend_schedule_raw)

    demand_rates_structure = [[_demand_band_to_tier(band) for band in bands] for bands in band_sets]

    if demand_rates_structure == [[{"rate": 0}]]:
        return {}

    result: URDBRate = {
        "demandratestructure": demand_rates_structure,
        "demandweekdayschedule": demand_weekday_schedule,
        "demandweekendschedule": demand_weekend_schedule,
    }
    if (demand_window := build_demand_window(scenario, library)) is not None:
        result["demandwindow"] = demand_window
    return result


def build_demand_window(scenario: Scenario, library: Library) -> int | None:
    rates = []
    windows: set[int] = set()
    for dt in iter_year(scenario.year, timedelta(days=1)):
        tariff = library.tariffs.get_tariff_at_date(scenario.master_tariff_id, dt)
        rates = [
            rate for rate in ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt) if filter_demand_rates(rate)
        ]
        for rate in rates:
            quantity_key = rate.get("quantity_key")
            if quantity_key is None:
                raise RateConversionError(rate, "Demand-based rates must include quantity_key")
            quantity = _get_quantity_property(library, quantity_key)
            lookback_interval = quantity.get("lookback_interval_quantity")
            if lookback_interval is None:
                raise RateConversionError(rate, "Quantity key must have lookback interval value")
            windows.add(lookback_interval)

    if len(windows) == 1:
        return sum(windows)
    library.record_issue(("demand_window_uncertain",), "Could not determine demand window")
    return None


def get_month_hour_bands(
    scenario: Scenario, library: Library, month: int, hour: int, day_filter: DayPredicate
) -> BandSet:
    bands = [
        get_raw_bands_at_datetime(scenario, library, dt)
        for dt in iter_sampled_datetimes(scenario.year, month, hour, day_filter)
    ]
    return average_aligned_bands(bands)


def get_raw_bands_at_datetime(scenario: Scenario, library: Library, dt: datetime) -> BandSet:
    """Return the combined demand bands that apply at one instant."""
    tariff = library.tariffs.get_tariff_at_date(scenario.master_tariff_id, dt)
    rates = [rate for rate in ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt) if filter_demand_rates(rate)]
    piecewise_bands: list[BandSet] = []
    for rate in rates:
        bands = get_rate_demand_bands_at_datetime(rate, scenario, library, dt)
        piecewise_bands.append(bands)
    return sum_piecewise_bands(piecewise_bands)


def get_rate_demand_bands_at_datetime(
    rate: TariffRateExtended,
    _scenario: Scenario,
    library: Library,
    dt: datetime,
) -> BandSet:
    if rate.get("variable_factor_key") is not None:
        raise RateConversionError(rate, "Demand-based rates cannot have variable factors")
    quantity_key = rate.get("quantity_key")
    if quantity_key is None:
        raise RateConversionError(rate, "Demand-based rates must include quantity_key")
    quantity_unit = _get_quantity_unit(library, quantity_key)
    if quantity_unit != _SUPPORTED_QUANTITY_KEY:
        raise RateConversionError(rate, f"Unsupported demand quantity unit: {quantity_unit}")
    bands = list(_filter_demand_bands(rate))

    bands_set: BandSet = []
    for band in bands:
        demand_upper_limit = band.get("demand_upper_limit")
        if demand_upper_limit is None:
            demand_upper_limit = inf
        rate_amount = band["rate_amount"]
        if rate_amount == 0 and (variable_rate_key := rate.get("variable_rate_key")) is not None:
            rate_amount = library.variables.lookup(variable_rate_key, dt)
        bands_set.append((demand_upper_limit, rate_amount))

    return bands_set


def filter_demand_rates(rate: TariffRateExtended) -> bool:
    return rate["charge_type"] == "DEMAND_BASED"


def _filter_demand_bands(rate: TariffRateExtended) -> Iterator[TariffRateBand]:
    bands = rate["rate_bands"]
    if not bands:
        raise RateConversionError(rate, "Demand-based rates must have non-empty bands")
    for band in bands:
        if band.get("has_consumption_limit"):
            raise RateConversionError(rate, "Demand bands with consumption limits are not supported")
        if band.get("consumption_upper_limit"):
            raise RateConversionError(rate, "Demand bands with consumption limits are not supported")
        if band.get("has_property_limit"):
            raise RateConversionError(rate, "Bands with property limits are not supported")
        if band.get("property_upper_limit"):
            raise RateConversionError(rate, "Bands with property limits are not supported")
        yield band


def _get_quantity_unit(library: Library, quantity_key: str) -> str | None:
    return _get_quantity_property(library, quantity_key).get("quantity_unit")


def _get_quantity_property(library: Library, quantity_key: str) -> TariffPropertyStandard:
    return next(
        p
        for tariff in library.tariffs.tariffs
        for p in tariff.get("properties", [])
        if p.get("quantity_key") == quantity_key
    )


def _demand_band_to_tier(band: Band) -> DemandTier:
    """Convert one internal band tuple into a URDB energy tier entry."""

    if band[0] == inf:
        return {"rate": band[1]}
    return {"rate": band[1], "max": band[0]}
