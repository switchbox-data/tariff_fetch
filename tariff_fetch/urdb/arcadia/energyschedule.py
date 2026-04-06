"""Convert Arcadia energy rates into URDB schedule and tier structures."""

from collections.abc import Collection
from datetime import datetime
from math import inf

from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import EnergyTier, URDBRate

from . import rateutils as ru
from .exception import RateConversionError
from .scenario import Scenario
from .shared import average_aligned_bands, is_weekday, is_weekend, iter_sampled_datetimes, sum_piecewise_bands
from .types import Band, BandSet, DayPredicate

PercentageModifiers = list[tuple[set[RateChargeClass], float]]
_ALLOWED_CHARGE_CLASSES: set[RateChargeClass] = {"DISTRIBUTION", "SUPPLY", "TRANSMISSION", "OTHER", "CONTRACTED"}


def build_energy_schedule(scenario: Scenario, library: Library) -> URDBRate:
    """Build the URDB energy schedule and rate structure for one scenario year."""

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
) -> BandSet:
    """Average the sampled energy bands for one month, hour, and day type."""

    bands = [
        get_raw_bands_at_datetime(scenario, library, dt)
        for dt in iter_sampled_datetimes(scenario.year, month, hour, day_filter)
    ]
    return average_aligned_bands(bands)


def get_raw_bands_at_datetime(scenario: Scenario, library: Library, dt: datetime) -> BandSet:
    """Return the combined consumption bands that apply at one instant."""

    tariff = library.tariffs.get_tariff_at_date(scenario.master_tariff_id, dt)
    rates = list(ru.tariff_iter_rates_for_dt(tariff, scenario, library, dt))
    percentage_modifiers = get_percentage_rates_at_datetime(rates, scenario, library, dt)
    piecewise_bands: list[BandSet] = []
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
) -> BandSet | None:
    """Convert one applicable consumption rate into URDB-style piecewise bands."""

    if rate.get("variable_factor_key") is not None:
        raise RateConversionError(rate, "Consumption-based rates cannot have variable factor")
    if rate.get("charge_type") != "CONSUMPTION_BASED":
        return None
    if rate.get("quantity_key") is not None:
        raise RateConversionError(rate, "Rates with quantity_key are not supported for consumption conversion")
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
    """Collect supported percentage-based modifiers that apply at one instant."""

    rates = [rate for rate in rates if ru.rate_get_band_units(rate) == {"PERCENTAGE"}]

    result: PercentageModifiers = []
    for rate in rates:
        if rate.get("quantity_key") is not None:
            raise RateConversionError(rate, "Rates with quantity_key are not supported for percentage conversion")
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


def _energy_band_to_tier(band: Band) -> EnergyTier:
    """Convert one internal band tuple into a URDB energy tier entry."""

    if band[0] == inf:
        return {"rate": band[1], "unit": "kWh"}
    return {"rate": band[1], "max": band[0], "unit": "kWh"}
