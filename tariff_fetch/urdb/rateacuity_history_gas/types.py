from datetime import date
from typing import Literal, Required, get_args

from typing_extensions import TypedDict, TypeIs

BandDeterminant = Literal["ccf", "therms", "cubic feet"]
ConsumptionRateDeterminant = Literal["per ccf", "per therm"]
PercentRateDeterminant = Literal["percent"]
FixedRateDeterminant = Literal["per month", "per month per location", "per month per meter", "per meter per month"]
RateDeterminant = Literal[ConsumptionRateDeterminant, PercentRateDeterminant, FixedRateDeterminant]
KnownRateDeterminant = RateDeterminant


class Row(TypedDict, total=False):
    rate: Required[str]
    effective_date: date | None
    season: str | None
    min_therms: float | None
    max_therms: float | None
    start: Required[float | None]
    end: Required[float | None]
    location: str
    determinant: BandDeterminant | None
    rate_determinant: Required[RateDeterminant]


def is_band_determinant(value: str) -> TypeIs[BandDeterminant]:
    return value in get_args(BandDeterminant)


def is_consumption_rate_determinant(value: str) -> TypeIs[ConsumptionRateDeterminant]:
    return value in get_args(ConsumptionRateDeterminant)


def is_rate_determinant(value: str) -> TypeIs[RateDeterminant]:
    return value in get_args(RateDeterminant)
