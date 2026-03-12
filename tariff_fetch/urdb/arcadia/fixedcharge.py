from collections.abc import Iterator
from datetime import datetime, timedelta
from statistics import mean

from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.schema import URDBRate

from . import rateutils as ru
from .exception import RateConversionError
from .library import Library
from .scenario import Scenario

_LOGGED: set[int] = set()


def build_fixed_charge(scenario: Scenario, library: Library) -> URDBRate:
    return {
        "fixedchargefirstmeter": get_fixed_charge_value(scenario, library),
        "fixedchargeunits": "$/month",
    }


def get_fixed_charge_value(scenario: Scenario, library: Library) -> float:
    return mean(get_fixed_charge_at_dt(scenario, library, dt) for dt in _iter_year(scenario.year, timedelta(hours=12)))


def get_fixed_charge_at_dt(scenario: Scenario, library: Library, dt: datetime) -> float:
    master_tariff_id = scenario.master_tariff_id
    tariff = library.tariffs.get_tariff_at_date(master_tariff_id, dt.date())
    rates = ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt)
    return sum(get_rate_fixed_charge_at_dt(scenario, library, rate, dt) for rate in rates)


def get_rate_fixed_charge_at_dt(scenario: Scenario, library: Library, rate: TariffRateExtended, dt: datetime) -> float:
    bands = ru.rate_filter_bands(rate, scenario, library)
    band_rate_units = {band["rate_unit"] for band in bands}
    if rate["charge_type"] != "FIXED_PRICE":
        return 0
    if (transaction_type := rate["transaction_type"]) != "BUY":
        raise RateConversionError(
            rate, f"Only BUY transaction type is supported for fixed charges (got {transaction_type})"
        )
    if "COST_PER_UNIT" not in band_rate_units:
        raise RateConversionError(rate, "Fixed price rate bands units should be COST_PER_UNIT")
    if rate["charge_period"] != "MONTHLY":
        raise RateConversionError(rate, "Fixed charges should be monthly")
    if len(band_rate_units) > 1:
        raise RateConversionError(rate, "More than one applicable band for percentage rate")
    band = bands[0]
    if band["has_consumption_limit"]:
        raise RateConversionError(rate, "Fixed rate bands cannot have has_consumption_limit==true")
    if band.get("consumption_upper_limit") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have consumption_upper_limit")
    if band["has_demand_limit"]:
        raise RateConversionError(rate, "Fixed rate bands cannot have has_demand_limit==true")
    if band.get("demand_upper_limit") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have demand_upper_limit")
    if band["has_property_limit"]:
        raise RateConversionError(rate, "Fixed rate bands cannot have has_property_limit==true")
    if band.get("property_upper_limit") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have property_upper_limit")
    if band.get("calculation_factor") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have calculation_factor")
    if band.get("applicability_formula") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have applicability_formula")

    rate_amount = ru.rate_band_get_amount_at_datetime(band, library, dt)
    if rate["tariff_rate_id"] not in _LOGGED:
        print(f"Applied fixed charge: {rate['rate_name']} ({rate['tariff_rate_id']}) ({rate_amount})")
        _LOGGED.add(rate["tariff_rate_id"])
    return rate_amount


def _iter_year(year: int, delta: timedelta) -> Iterator[datetime]:
    dt = datetime(year, 1, 1, 0, 30, 0)
    max_dt = datetime(year + 1, 1, 1, 0, 0, 0)
    while dt < max_dt:
        yield dt
        dt += delta
