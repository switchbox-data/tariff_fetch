import calendar
import itertools
from collections.abc import Callable, Collection
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from math import inf
from statistics import mean

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.arcadia.schema.season import SeasonExtended
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended
from tariff_fetch.arcadia.schema.timeofuse import Period, TimeOfUseExtended

# =========================
# Types
# =========================

Band = tuple[float, float]  # (upper_limit, value)
BandSet = list[Band]
DayPredicate = Callable[[datetime], bool]
PercentageModifiers = list[tuple[set[RateChargeClass], float]]


# =========================
# Scenario
# =========================


@dataclass(frozen=True)
class Scenario:
    territory_id: int
    year: int
    quantities: dict[str, float | int] = field(default_factory=dict)


# =========================
# Public entry points
# =========================


def build_urdb(
    api: ArcadiaSignalAPI,
    tariff: TariffExtended,
    scenario: Scenario,
):
    return {
        "energyweekdayschedule": build_energy_schedule(api, tariff, scenario, is_weekday),
        "energyweekendschedule": build_energy_schedule(api, tariff, scenario, is_weekend),
    }


def build_energy_schedule(
    api: ArcadiaSignalAPI,
    tariff: TariffExtended,
    scenario: Scenario,
    day_filter: DayPredicate,
) -> list[list[BandSet]]:
    """
    Builds a 12x24 URDB energy schedule by sampling real calendar days
    and averaging resulting tariff bands.
    """
    return [
        [build_month_hour_bands(api, tariff, scenario, month, hour, day_filter) for hour in range(24)]
        for month in range(1, 13)
    ]


# =========================
# Sampling logic
# =========================


def sample_datetime(year: int, month: int, day: int, hour: int) -> datetime:
    """
    Representative instant for tariff evaluation.

    We intentionally sample at hh:30 to avoid boundary effects and
    because Arcadia TOU periods are hour-granular.
    """
    return datetime(year, month, day, hour, 30)


def iter_sampled_datetimes(
    year: int,
    month: int,
    hour: int,
    day_filter: DayPredicate,
):
    _, days = calendar.monthrange(year, month)

    for day in range(1, days + 1):
        calendar_day = datetime(year, month, day)
        if day_filter(calendar_day):
            yield sample_datetime(year, month, day, hour)


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


# =========================
# Month/hour aggregation
# =========================


def build_month_hour_bands(
    api: ArcadiaSignalAPI,
    tariff: TariffExtended,
    scenario: Scenario,
    month: int,
    hour: int,
    day_filter: DayPredicate,
) -> BandSet:
    bands = [
        get_tariff_bands_at_datetime(api, tariff, scenario, dt)
        for dt in iter_sampled_datetimes(scenario.year, month, hour, day_filter)
    ]
    return average_aligned_bands(bands)


# =========================

# Tariff evaluation
# =========================


def get_tariff_bands_at_datetime(
    api: ArcadiaSignalAPI,
    tariff: TariffExtended,
    scenario: Scenario,
    dt: datetime,
) -> BandSet:
    rates = tariff.get("rates", [])
    percentage_modifiers = get_percentage_modifiers_at_datetime(api, tariff, scenario, dt)
    band_sets = [get_rate_bands_at_datetime(api, rate, scenario, percentage_modifiers, dt) for rate in rates]
    return sum_piecewise_bands([bands for bands in band_sets if bands is not None])


def get_rate_bands_at_datetime(
    api: ArcadiaSignalAPI,
    rate: TariffRateExtended,
    scenario: Scenario,
    percentage_modifiers: PercentageModifiers,
    dt: datetime,
) -> BandSet | None:
    if rate.get("charge_type") != "CONSUMPTION_BASED":
        return None
    if not is_rate_applies_to_scenario(rate, scenario):
        return None
    if not is_rate_applies_to_datetime(rate, dt):
        return None

    rate_bands = rate.get("rate_bands") or []
    if not rate_bands:
        return None

    if any(b["rate_unit"] != "COST_PER_UNIT" for b in rate_bands):
        raise RuntimeError("Unsupported or mixed rate units")

    if "variable_rate_key" not in rate:
        raw_result = [(band.get("consumption_upper_limit") or inf, band["rate_amount"]) for band in rate_bands]
    else:
        if len(rate_bands) > 1:
            raise RuntimeError("Variable rate with limits")

        value = lookup_variable_rate(
            api,
            rate["variable_rate_key"],
            dt,
        )
        raw_result = [(rate_bands[0].get("property_upper_limit") or inf, value)]

    charge_classes = set(rate.get("charge_class") or [])

    charge_multiplier = 1.0 + sum(
        modifier_value for modifier_classes, modifier_value in percentage_modifiers if charge_classes & modifier_classes
    )

    return [(limit, value * charge_multiplier) for limit, value in raw_result]


def get_percentage_modifiers_at_datetime(
    api: ArcadiaSignalAPI, tariff: TariffExtended, scenario: Scenario, dt: datetime
):
    rates = tariff.get("rates", [])
    result: PercentageModifiers = []
    for rate in rates:
        if not is_rate_applies_to_scenario(rate, scenario):
            continue
        if not is_rate_applies_to_datetime(rate, dt):
            continue
        if rate.get("charge_type") != "QUANTITY":
            continue
        rate_bands = rate.get("rate_bands") or []
        if not rate_bands:
            continue
        if rate_bands[0]["rate_unit"] != "PERCENTAGE":
            continue
        if len(rate_bands) > 1:
            raise RuntimeError("Unsupported multiple percentage bands")
        if "variable_rate_key" in rate:
            raise RuntimeError("Variable rate key for percentage bands are not supported yet")

        if (charge_classes := rate.get("charge_class")) is None:
            raise RuntimeError("No charge class")

        rate_amount = rate_bands[0]["rate_amount"]
        result.append((set(charge_classes), rate_amount / 100.0))
    return result


def lookup_variable_rate(
    api: ArcadiaSignalAPI,
    key: str,
    dt: datetime,
) -> float:
    lookups = lookup_property_timeseries(api, key, dt.year)
    for row in lookups:
        if row["from_date_time"] <= dt <= (row["to_date_time"] or datetime.max):
            return row["best_value"] or row["actual_value"] or row["forecast_value"] or 0.0
    return 0.0


# =========================
# Band math
# =========================


def average_aligned_bands(inputs: list[BandSet]) -> BandSet:
    if not inputs:
        return []

    limits = [limit for limit, _ in inputs[0]]
    if not all([limit for limit, _ in bands] == limits for bands in inputs):
        raise ValueError("All band limits must be identical to average")

    return [(limit, mean(bands[i][1] for bands in inputs)) for i, limit in enumerate(limits)]


def sum_piecewise_bands(inputs: Collection[BandSet]) -> BandSet:
    if not inputs:
        return []

    normalized = [sorted(bands, key=lambda b: b[0]) for bands in inputs]
    limits = sorted({limit for bands in normalized for limit, _ in bands})

    def value_at(bands: BandSet, limit: float) -> float:
        for band_limit, value in bands:
            if limit <= band_limit:
                return value
        return 0.0

    summed = [(limit, sum(value_at(bands, limit) for bands in normalized)) for limit in limits]

    return [a for a, b in itertools.pairwise(summed) if a[1] != b[1]] + [summed[-1]]


# =========================
# Applicability rules
# =========================


def is_rate_applies_to_scenario(
    rate: TariffRateExtended,
    scenario: Scenario,
) -> bool:
    territory = rate.get("territory")
    if territory is None:
        return True
    return territory["territory_id"] == scenario.territory_id


def is_rate_applies_to_datetime(
    rate: TariffRateExtended,
    dt: datetime,
) -> bool:
    season = rate.get("season")
    if season and not is_datetime_within_season(season, dt):
        return False

    tou = rate.get("time_of_use")
    if tou and not is_datetime_within_tou(tou, dt):
        return False

    return True


def is_datetime_within_tou(
    tou: TimeOfUseExtended,
    dt: datetime,
) -> bool:
    season = tou.get("season")
    if season and not is_datetime_within_season(season, dt):
        return False

    return any(is_datetime_within_period(period, dt) for period in tou["tou_periods"])


def is_datetime_within_period(
    period: Period,
    dt: datetime,
) -> bool:
    return (
        period["from_day_of_week"] <= dt.weekday() <= period["to_day_of_week"]
        and period["from_hour"] <= dt.hour <= period["to_hour"]
        and period["from_minute"] <= dt.minute <= period["to_minute"]
    )


def is_rate_unchanging(rate: TariffRateExtended) -> bool:
    if "season" in rate:
        return False
    if "time_of_use" in rate:
        return False
    if len(rate["rate_bands"]) != 1:
        return False
    if "variable_rate_key" in rate:
        return False
    return True


# =========================
# Season logic
# =========================


def is_datetime_within_season(
    season: SeasonExtended,
    dt: datetime,
) -> bool:
    start_month, end_month = season_billing_period(season)

    start = datetime(dt.year, start_month, 1)
    end = datetime(dt.year + (end_month == 12), (end_month % 12) + 1, 1)

    if start < end:
        return start <= dt < end
    return dt >= start or dt < end


def season_billing_period(season: SeasonExtended) -> tuple[int, int]:
    start = season["season_from_month"]
    end = season["season_to_month"]

    if season.get("from_edge_predominance") == "SUBSERVIENT" or (
        season.get("from_edge_predominance") is None and season["season_from_day"] > 15
    ):
        start += 1

    if season.get("to_edge_predominance") == "PREDOMINANT" or (
        season.get("to_edge_predominance") is None and season["season_to_day"] < 16
    ):
        end -= 1

    return (start - 1) % 12 + 1, (end - 1) % 12 + 1


# =========================
# Property lookup
# =========================


@lru_cache(maxsize=256)
def lookup_property_timeseries(api: ArcadiaSignalAPI, key: str, year: int):
    return list(
        api.properties.lookups.iter_pages(
            key,
            from_date_time=date(year, 1, 1),
            to_date_time=date(year + 1, 1, 1),
        )
    )
