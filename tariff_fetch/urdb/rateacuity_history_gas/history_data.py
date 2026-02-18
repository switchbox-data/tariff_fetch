import contextlib
from collections.abc import Iterator
from datetime import datetime
from math import inf
from typing import Any, cast, final, override

import polars as pl
from pydantic import BaseModel, TypeAdapter, ValidationError

from .exceptions import IncorrectDataframeSchemaMonths, IncorrectDataframeSchemaMultipleYears
from .shared import is_date_column_name, kwh_multiplier
from .types import (
    BandDeterminant,
    ConsumptionRateDeterminant,
    FixedRateDeterminant,
    PercentRateDeterminant,
)


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
    season: str | None
    effective_date: str | None
    start: float | None = None
    end: float | None = None
    # rate_determinant: RateDeterminant
    determinant: BandDeterminant | None = None
    location: str | None = None
    month_values: list[float | None]
    location_avg_factor: float

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
        result = max(0, raw_value / kwh_multiplier(self.rate_determinant))
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
