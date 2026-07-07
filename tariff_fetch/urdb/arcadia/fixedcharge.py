"""Convert Arcadia fixed-price charges into a single URDB fixed charge."""

import calendar
from collections.abc import Iterator
from datetime import datetime, timedelta
from statistics import mean

from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.schema import URDBRate

from . import rateutils as ru
from .exception import RateConversionError
from .library import Library
from .scenario import Scenario


def build_fixed_charge(scenario: Scenario, library: Library) -> URDBRate:
    """Build the URDB fixed-charge fields for a scenario."""

    return {
        "fixedchargefirstmeter": get_fixed_charge_value(scenario, library),
        "fixedchargeunits": "$/month",
    }


def get_fixed_charge_value(scenario: Scenario, library: Library) -> float:
    """Average the sampled fixed charge across the target year."""

    return (
        sum(
            mean(
                get_fixed_charge_at_dt(scenario, library, dt)
                for dt in _iter_month(scenario.year, month, timedelta(hours=8))
            )
            for month in range(1, 13)
        )
        / 12
    )


def get_fixed_charge_at_dt(scenario: Scenario, library: Library, dt: datetime) -> float:
    """Sum all applicable fixed-price rates at one sampled instant."""

    master_tariff_id = scenario.master_tariff_id
    tariff = library.tariffs.get_tariff_at_date(master_tariff_id, dt.date())
    rates = ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt)
    rates = list(rates)
    return sum(get_rate_fixed_charge_at_dt(scenario, library, rate, dt) for rate in rates)


def get_rate_fixed_charge_at_dt(scenario: Scenario, library: Library, rate: TariffRateExtended, dt: datetime) -> float:
    """Convert one applicable Arcadia rate into a fixed-charge amount at one instant."""

    bands = ru.rate_filter_bands(rate, scenario, library)
    if rate["charge_type"] != "FIXED_PRICE":
        return 0
    if not bands:
        return 0
    if (variable_factor_key := rate.get("variable_factor_key")) is not None and not (
        rate["charge_period"] == "MONTHLY" and variable_factor_key == "billingPeriodProrationFactor"
    ):
        raise RateConversionError(rate, "Fixed charges cannot have variable factors")
    if rate.get("quantity_key") is not None:
        raise RateConversionError(rate, "Rates with quantity_key are not supported for fixed charge conversion")
    band_rate_units = {band["rate_unit"] for band in bands}
    if (transaction_type := rate["transaction_type"]) != "BUY":
        raise RateConversionError(
            rate, f"Only BUY transaction type is supported for fixed charges (got {transaction_type})"
        )
    if "COST_PER_UNIT" not in band_rate_units:
        raise RateConversionError(rate, "Fixed price rate bands units should be COST_PER_UNIT")
    if (charge_period := rate["charge_period"]) not in {"MONTHLY", "DAILY"}:
        raise RateConversionError(rate, f"Fixed charges should be monthly or daily (got {charge_period})")
    if len(bands) > 1:
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
    if band.get("applicability_formula") is not None:
        raise RateConversionError(rate, "Fixed rate bands cannot have applicability_formula")

    rate_amount = ru.rate_band_get_amount_at_datetime(band, library, dt)
    rate_amount = normalize_fixed_charge_amount(rate_amount, charge_period, dt)
    if variable_factor_key == "billingPeriodProrationFactor":
        _, days = calendar.monthrange(dt.year, dt.month)
        multiplier = days / 30
        rate_amount *= multiplier

    return rate_amount


def normalize_fixed_charge_amount(rate_amount: float, charge_period: str, dt: datetime) -> float:
    """Normalize a supported fixed charge into monthly units."""

    if charge_period == "MONTHLY":
        return rate_amount
    if charge_period == "DAILY":
        return rate_amount * calendar.monthrange(dt.year, dt.month)[1]
    raise ValueError(f"Unsupported fixed charge period: {charge_period}")


def _iter_month(year: int, month: int, delta: timedelta) -> Iterator[datetime]:
    dt = datetime(year, month, 1, hour=0, minute=30, second=0)
    max_dt = datetime(year + 1, 1, 1, 0, 0, 0) if month == 12 else datetime(year, month + 1, 1, 0, 0, 0)
    while dt < max_dt:
        yield dt
        dt += delta
