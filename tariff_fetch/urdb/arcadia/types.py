"""Shared type aliases used by the Arcadia-to-URDB converter."""

from collections.abc import Callable
from datetime import datetime

from tariff_fetch.arcadia.schema.common import RateChargeClass

Band = tuple[float, float]  # (upper_limit, value)
BandSet = list[Band]
DayPredicate = Callable[[datetime], bool]
PercentageModifiers = list[tuple[set[RateChargeClass], float]]
