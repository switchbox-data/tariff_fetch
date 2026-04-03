from collections.abc import Iterator
from datetime import datetime
from math import inf

from tariff_fetch.arcadia.schema.tariffrate import TariffRateBand, TariffRateExtended
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.schema import URDBRate

from . import rateutils as ru
from .library import Library
from .scenario import Scenario
from .shared import sum_piecewise_bands
from .types import Band, BandSet

_SUPPORTED_QUANTITY_KEY = "kW"


def build_demand_schedule(scenario: Scenario, library: Library) -> URDBRate: ...


def get_raw_bands_at_datetime(scenario: Scenario, library: Library, dt: datetime) -> BandSet:
    """Return the combined demand bands that apply at one instant."""
    tariff = library.tariffs.get_tariff_at_date(scenario.master_tariff_id, dt)
    rates = list(ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt))
    piecewise_bands: list[BandSet] = []
    for rate in rates:
        bands = get_rate_demand_bands_at_datetime(rate, scenario, library, dt)
        if bands is None:
            continue
        piecewise_bands.append(bands)
    return sum_piecewise_bands(piecewise_bands)


def get_rate_demand_bands_at_datetime(
    rate: TariffRateExtended,
    scenario: Scenario,
    library: Library,
    dt: datetime,
) -> BandSet | None:
    if rate["charge_type"] != "DEMAND_BASED":
        return None
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


def _get_quantity_unit(library: Library, property_key: str) -> str | None:
    return library.tariffs.get_property(property_key).get("quantity_unit")
