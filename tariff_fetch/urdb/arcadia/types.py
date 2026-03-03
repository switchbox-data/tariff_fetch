from collections.abc import Callable
from datetime import datetime

from tariff_fetch.arcadia.schema.common import RateChargeClass

ConsumptionBand = tuple[float, float]  # (upper_limit, value)
ConsumptionBandSet = list[ConsumptionBand]
DayPredicate = Callable[[datetime], bool]
PercentageModifiers = list[tuple[set[RateChargeClass], float]]
