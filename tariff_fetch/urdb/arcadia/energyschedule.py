import itertools
from collections.abc import Collection
from datetime import datetime
from math import inf
from statistics import mean

from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import EnergyTier, URDBRate

from . import rateutils as ru
from .exception import RateConversionError
from .scenario import Scenario
from .shared import is_weekday, is_weekend, iter_sampled_datetimes
from .types import ConsumptionBand, ConsumptionBandSet, DayPredicate

PercentageModifiers = list[tuple[set[RateChargeClass], float]]
_ALLOWED_CHARGE_CLASSES: set[RateChargeClass] = {"DISTRIBUTION", "SUPPLY", "TRANSMISSION", "OTHER", "CONTRACTED"}


_RATE_PRECISION = 6


def build_energy_schedule(scenario: Scenario, library: Library) -> URDBRate:
    weekday_schedule_raw = [
        [get_month_hour_bands(scenario, library, month, hour, is_weekday) for hour in range(24)]
        for month in range(1, 13)
    ]
    weekend_schedule_raw = [
        [get_month_hour_bands(scenario, library, month, hour, is_weekend) for hour in range(24)]
        for month in range(1, 13)
    ]

    # Order-preserving unique band sets
    band_sets: list[tuple[ConsumptionBand, ...]] = []
    band_index: dict[tuple[ConsumptionBand, ...], int] = {}

    for schedule in (weekday_schedule_raw, weekend_schedule_raw):
        for month in schedule:
            for bands in month:
                key = tuple(bands)
                if key not in band_index:
                    band_index[key] = len(band_sets)
                    band_sets.append(key)

    energy_weekday_schedule = tuple(tuple(band_index[tuple(hour)] for hour in month) for month in weekday_schedule_raw)
    energy_weekend_schedule = tuple(tuple(band_index[tuple(hour)] for hour in month) for month in weekend_schedule_raw)

    energy_rates_structure = [[_energy_band_to_tier(band) for band in bands] for bands in band_sets]

    return {
        "energyratestructure": energy_rates_structure,
        "energyweekdayschedule": energy_weekday_schedule,
        "energyweekendschedule": energy_weekend_schedule,
    }


def get_month_hour_bands(
    scenario: Scenario,
    library: Library,
    month: int,
    hour: int,
    day_filter: DayPredicate,
) -> ConsumptionBandSet:
    """Get raw consumption bands for specific month/hour"""
    bands = [
        get_raw_bands_at_datetime(scenario, library, dt)
        for dt in iter_sampled_datetimes(scenario.year, month, hour, day_filter)
    ]
    return average_aligned_bands(bands)


def get_raw_bands_at_datetime(scenario: Scenario, library: Library, dt: datetime) -> ConsumptionBandSet:
    """Get raw tariff consumption-based bands at datetime dt"""
    tariff = library.tariffs.get_tariff_at_date(scenario.master_tariff_id, dt)
    rates = list(ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt))
    percentage_modifiers = get_percentage_rates_at_datetime(rates, scenario, library, dt)
    piecewise_bands: list[ConsumptionBandSet] = []
    for rate in rates:
        rate_bands = get_rate_consumption_bands_at_datetime(rate, scenario, library, dt)
        if rate_bands is None:
            continue
        # Apply percentage modifiers
        charge_classes = set(rate.get("charge_class") or [])
        charge_multiplier = 1.0 + sum(mv for mc, mv in percentage_modifiers if charge_classes & mc)
        if scenario.apply_percentages:
            rate_bands = [(limit, value * charge_multiplier) for limit, value in rate_bands]
        piecewise_bands.append(rate_bands)

    return sum_piecewise_bands(piecewise_bands)


def get_rate_consumption_bands_at_datetime(
    rate: TariffRateExtended,
    scenario: Scenario,
    library: Library,
    dt: datetime,
) -> ConsumptionBandSet | None:
    if rate.get("charge_type") != "CONSUMPTION_BASED":
        return None
    if (transaction_type := rate["transaction_type"]) not in {"BUY", "NET", "BUY_IMPORT"}:
        raise RateConversionError(
            rate,
            f"Only BUY, BUY_IMPORT, and NET transactions are supported for consumption rates (got {transaction_type})",
        )
    if set(rate.get("charge_class", [])) - _ALLOWED_CHARGE_CLASSES:
        raise RateConversionError(rate, "Incorrect charge class for consumption-based rate")
    if rate["charge_period"] != "MONTHLY":
        raise RateConversionError(rate, "Incorrect charge period for consumption-based rate")
    bands = ru.rate_filter_bands(rate, scenario, library)

    if any(band["rate_unit"] != "COST_PER_UNIT" for band in bands):
        raise RateConversionError(rate, "Consumption bands must have rate unit = COST_PER_UNIT")

    return [
        (ru.band_consumption_upper_limit(band), ru.rate_band_get_amount_at_datetime(band, library, dt))
        for band in bands
    ]


def get_percentage_rates_at_datetime(
    rates: Collection[TariffRateExtended], scenario: Scenario, library: Library, dt: datetime
) -> PercentageModifiers:
    rates = [rate for rate in rates if ru.rate_get_band_units(rate) == {"PERCENTAGE"}]

    result: PercentageModifiers = []
    for rate in rates:
        if (transaction_type := rate["transaction_type"]) not in {"BUY", "NET", "BUY_IMPORT"}:
            raise RateConversionError(
                rate,
                f"Only BUY, BUY_IMPORT, and NET transactions are supported for percentage rates (got {transaction_type})",
            )
        if rate["charge_period"] != "MONTHLY":
            raise RateConversionError(rate, "Incorrect charge period for percentage-based rate")
        if not (bands := ru.rate_filter_bands(rate, scenario, library)):
            raise RateConversionError(rate, "No bands for percentage rate")

        # if not (bands := ru.rate_filter_bands(rate, scenario)):
        #    raise RateConversionError(rate, "No bands for percentage rate")
        if len(bands) > 1:
            raise RateConversionError(rate, "Multiple bands are not supported for percentage rates")
        if (charge_classes := rate.get("charge_class")) is None:
            continue
        band = bands[0]
        if band["is_credit"]:
            raise RateConversionError(rate, "Credit rates are not supported for pecentage rates")

        rate_amount = ru.rate_band_get_amount_at_datetime(band, library, dt)
        result.append((set(charge_classes), rate_amount / 100.0))
    return result


def sum_piecewise_bands(inputs: Collection[ConsumptionBandSet]) -> ConsumptionBandSet:
    if not inputs:
        return []

    normalized = [sorted(bands, key=lambda b: b[0]) for bands in inputs]
    limits = sorted({limit for bands in normalized for limit, _ in bands})

    def value_at(bands: ConsumptionBandSet, limit: float) -> float:
        for band_limit, value in bands:
            if limit <= band_limit:
                return value
        return 0.0

    summed = [(limit, sum(value_at(bands, limit) for bands in normalized)) for limit in limits]

    return [a for a, b in itertools.pairwise(summed) if a[1] != b[1]] + [summed[-1]]


def average_aligned_bands(inputs: list[ConsumptionBandSet]) -> ConsumptionBandSet:
    if not inputs:
        return []

    normalized = [sorted(bands, key=lambda b: b[0]) for bands in inputs]
    limits = sorted({limit for bands in normalized for limit, _ in bands})

    def value_at(bands: ConsumptionBandSet, limit: float) -> float:
        for band_limit, value in bands:
            if limit <= band_limit:
                return value
        return 0.0

    averaged = [
        (limit, round(mean(value_at(bands, limit) for bands in normalized), _RATE_PRECISION)) for limit in limits
    ]

    # Collapse consecutive identical values
    result = [averaged[0]]
    for limit, value in averaged[1:]:
        if value != result[-1][1]:
            result.append((limit, value))

    return result


def _energy_band_to_tier(band: ConsumptionBand) -> EnergyTier:
    if band[0] == inf:
        return {"rate": band[1], "unit": "kWh"}
    return {"rate": band[1], "max": band[0], "unit": "kWh"}
