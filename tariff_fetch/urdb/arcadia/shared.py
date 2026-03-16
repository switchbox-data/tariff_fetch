"""Small shared helpers for Arcadia schedule sampling and date classification."""

import calendar
from datetime import date, datetime
from functools import lru_cache

from tariff_fetch.arcadia.api import ArcadiaSignalAPI

from .types import DayPredicate


def as_naive_datetime(dt: datetime) -> datetime:
    """Drop timezone metadata so Arcadia timestamps compare as local wall-clock datetimes."""

    return dt.replace(tzinfo=None)


def iter_sampled_datetimes(
    year: int,
    month: int,
    hour: int,
    day_filter: DayPredicate,
):
    """Yield representative datetimes for all matching days in a month/hour bucket."""

    _, days = calendar.monthrange(year, month)

    for day in range(1, days + 1):
        calendar_day = datetime(year, month, day)
        if day_filter(calendar_day):
            yield sample_datetime(year, month, day, hour)


def sample_datetime(year: int, month: int, day: int, hour: int) -> datetime:
    """
    Representative instant for tariff evaluation.

    We intentionally sample at hh:30 to avoid boundary effects and
    because Arcadia TOU periods are hour-granular.
    """
    return datetime(year, month, day, hour, 30)


def is_weekday(dt: datetime) -> bool:
    """Return whether a datetime falls on a weekday."""

    return dt.weekday() < 5


def is_weekend(dt: datetime) -> bool:
    """Return whether a datetime falls on a weekend."""

    return dt.weekday() >= 5


def lookup_variable_rate(
    api: ArcadiaSignalAPI,
    key: str,
    dt: datetime,
) -> float:
    """Look up one variable Arcadia rate value at a specific datetime."""

    lookups = lookup_property_timeseries(api, key, dt.year)
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


@lru_cache(maxsize=256)
def lookup_property_timeseries(api: ArcadiaSignalAPI, key: str, year: int):
    """Fetch and cache one year of variable lookup rows for a property key."""

    return list(
        api.properties.lookups.iter_pages(
            key,
            from_date_time=date(year, 1, 1),
            to_date_time=date(year + 1, 1, 1),
        )
    )
