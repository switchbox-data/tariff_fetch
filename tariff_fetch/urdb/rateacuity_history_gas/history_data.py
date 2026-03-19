import contextlib
import re
from calendar import monthrange
from collections.abc import Iterator
from datetime import datetime
from math import inf
from typing import Any, NamedTuple, cast, final

import polars as pl
from pydantic import BaseModel, TypeAdapter, ValidationError, field_validator
from typing_extensions import override

from .exceptions import IncorrectDataframeSchemaMonths, IncorrectDataframeSchemaMultipleYears
from .shared import is_date_column_name, kwh_multiplier
from .types import (
    BandDeterminant,
    ConsumptionRateDeterminant,
    FixedRateDeterminant,
    PercentRateDeterminant,
)


class DayOfMonth(NamedTuple):
    day: int
    month: int


class Season(NamedTuple):
    start: DayOfMonth
    end: DayOfMonth


_SEASON_PATTERN = re.compile(r"^\s*(\d{2})/(\d{2})\s*-\s*(\d{2})/(\d{2})\s*$")


@final
class RowValidationError(Exception):
    def __init__(self, row: dict[str, Any]) -> None:  # pyright: ignore[reportExplicitAny]
        super().__init__()
        self.row = row

    @override
    def __str__(self) -> str:
        return f"Cannot validate row: {self.row}"


@final
class HistoryData:
    def __init__(self, df: pl.DataFrame) -> None:
        self._df = df

    def rows(self) -> Iterator["Row"]:
        month_column_names = _get_month_column_names(self._df)
        location_avg_factor = self.location_avg_factor()
        for row_dict in self._df.iter_rows(named=True):
            with contextlib.suppress(RowValidationError):
                yield _row_to_model(row_dict, location_avg_factor, month_column_names)

    def get_unknown_nonempty_columns(self) -> list[str]:
        df = self._df
        df_schema = df.schema
        non_date_columns = {col for col in df_schema if not is_date_column_name(col)}
        allow_empty_columns = non_date_columns - FixedChargeRow.model_fields.keys()
        return [
            c
            for c in allow_empty_columns
            if not (df[c].is_null() | (df[c] == "" if df[c].dtype == pl.Utf8 else False)).all()
        ]

    def validate_rows(self) -> list[RowValidationError]:
        result: list[RowValidationError] = []
        month_column_names = _get_month_column_names(self._df)
        location_avg_factor = self.location_avg_factor()
        for row_dict in self._df.iter_rows(named=True):
            try:
                _ = _row_to_model(row_dict, location_avg_factor, month_column_names)
            except RowValidationError as e:
                result.append(e)
        return result

    def location_avg_factor(self) -> float:
        if "location" not in self._df.schema:
            return 1
        count = cast(
            int,
            self._df.select(  # pyright: ignore[reportUnknownMemberType]
                pl.col("location").filter(pl.col("location").is_not_null() & (pl.col("location") != "")).n_unique()
            ).item(),
        )
        if count == 0:
            return 1
        return 1 / count


class _Row(BaseModel):
    rate: str
    season: Season | None
    year: int
    effective_date: str | None
    start: float | None = None
    end: float | None = None
    # rate_determinant: RateDeterminant
    determinant: BandDeterminant | None = None
    location: str | None = None
    month_values: list[float | None]
    location_avg_factor: float

    @field_validator("season", mode="before")
    @classmethod
    def _parse_season(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, Season):
            return value
        if not isinstance(value, str):
            return value
        match = _SEASON_PATTERN.fullmatch(value)
        if match is None:
            return value
        start_month, start_day, end_month, end_day = (int(part) for part in match.groups())
        return Season(
            start=_validated_day_of_month(start_month, start_day),
            end=_validated_day_of_month(end_month, end_day),
        )

    @property
    def start_kwh(self) -> float:
        if self.determinant is None:
            return 0
        if self.start is not None:
            return round(self.start * kwh_multiplier(self.determinant))
        return 0

    @property
    def end_kwh(self) -> float:
        if self.determinant is None:
            return inf
        if self.end is not None:
            return round(self.end * kwh_multiplier(self.determinant))
        return inf


class ConsumptionRow(_Row):
    rate_determinant: ConsumptionRateDeterminant

    def month_value_kwh(
        self,
        month: int,
    ) -> float:
        raw_value = self.month_values[month]
        if raw_value is None:
            return 0
        result = raw_value / kwh_multiplier(self.rate_determinant)
        if self.location:
            result *= self.location_avg_factor
        return result


class PercentageRow(_Row):
    rate_determinant: PercentRateDeterminant

    def month_value_float(self, month: int) -> float:
        raw_value = self.month_values[month]
        if raw_value is None:
            return 0
        result = raw_value / 100
        if self.location:
            result *= self.location_avg_factor
        return result


class FixedChargeRow(_Row):
    rate_determinant: FixedRateDeterminant

    def month_value(self, month: int) -> float:
        raw_value = self.month_values[month]
        if raw_value is None:
            return 0
        return raw_value


Row = ConsumptionRow | PercentageRow | FixedChargeRow


def _row_to_model(row: dict[str, Any], location_avg_factor: float, month_column_names: list[str]) -> Row:  # pyright: ignore[reportExplicitAny]
    result = row.copy()
    result["month_values"] = []
    result["year"] = datetime.strptime(month_column_names[0], "%m/%d/%Y").year
    for col in month_column_names:
        value = cast(float | None, row[col])
        del result[col]
        result["month_values"].append(value)  # pyright: ignore[reportUnknownMemberType]
    result["location_avg_factor"] = location_avg_factor
    ta: TypeAdapter[Row] = TypeAdapter(Row)
    try:
        return ta.validate_python(result)
    except ValidationError:
        raise RowValidationError(result) from None


def _get_month_column_names(df: pl.DataFrame):
    date_columns = [col for col in df.columns if is_date_column_name(col)]
    date_columns = sorted(date_columns, key=lambda c: datetime.strptime(c, "%m/%d/%Y").month)
    date_columns_datetimes = [datetime.strptime(c, "%m/%d/%Y") for c in date_columns]
    if [c.month for c in date_columns_datetimes] != list(range(1, 13)):
        raise IncorrectDataframeSchemaMonths()
    if len({c.year for c in date_columns_datetimes}) != 1:
        raise IncorrectDataframeSchemaMultipleYears()
    return date_columns


def _validated_day_of_month(month: int, day: int) -> DayOfMonth:
    if not 1 <= month <= 12:
        raise ValueError(f"Invalid season month: {month}")
    # Use a leap year so recurring seasonal boundaries can represent Feb 29.
    if not 1 <= day <= monthrange(2024, month)[1]:
        raise ValueError(f"Invalid season day {day} for month {month}")
    return DayOfMonth(day=day, month=month)
