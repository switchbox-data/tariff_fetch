import itertools
import re
from collections.abc import Iterable
from datetime import date, datetime
from math import inf
from statistics import mean
from typing import Literal, Required, TypedDict, cast, final, get_args, override

import polars as pl
from typing_extensions import TypeIs

from tariff_fetch.urdb.schema import EnergyTier, MonthSchedule, URDBRate

_EXPECTED_SCHEMA = {
    "rate": pl.String,
    "effective_date": str,
    # "season": pl.String,
    "min_therms": pl.Float64,
    "max_therms": pl.Float64,
    # "start": pl.String,
    # "end": pl.String,
    "determinant": pl.String,
    "rate_determinant": pl.String,
}

_DATE_COL_RE = re.compile(r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(\d{4})$")

BandDeterminant = Literal["ccf", "therms"]
ConsumptionRateDeterminant = Literal["per ccf", "per therm"]
PercentRateDeterminant = Literal["percent"]
FixedRateDeterminant = Literal["per month"]
RateDeterminant = Literal[ConsumptionRateDeterminant, PercentRateDeterminant, FixedRateDeterminant]
OtherRateDeterminant = Literal["per month per location", "per month per meter"]
KnownRateDeterminant = Literal[RateDeterminant, OtherRateDeterminant]

KNOWN_COLUMNS = [
    "rate",
    "effective_date",
    "season",
    "start",
    "end",
    "location",
    "determinant",
    "rate_determinant",
    "charge_type",
]

ALLOW_EMPTY_COLUMNS = [
    "min_therms",
    "max_therms",
    "min_psig",
    "max_psig",
]


@final
class IncorrectDataframeSchemaMonths(ValueError):
    @override
    def __str__(self) -> str:
        return "Incorrect months"


@final
class IncorrectDataframeSchemaMultipleYears(ValueError):
    @override
    def __str__(self) -> str:
        return "Multiple years in the dataframe"


class Row(TypedDict, total=False):
    rate: str
    effective_date: date | None
    season: str | None
    min_therms: float | None
    max_therms: float | None
    start: Required[float | None]
    end: Required[float | None]
    location: str
    determinant: BandDeterminant | None
    rate_determinant: Required[RateDeterminant]


def build_urdb(df: pl.DataFrame) -> URDBRate:
    df = df.with_columns(  # pyright: ignore[reportUnknownMemberType]
        pl.col(pl.Utf8).str.to_lowercase()
    )
    location_avg_factor = _get_location_avg_factor(df)
    month_taxes = _get_average_month_tax(df, location_avg_factor)
    energy_schedule = build_energy_schedule_raw(df, location_avg_factor, month_taxes)
    static_charges = _build_static_charges(df, location_avg_factor)
    return {**energy_schedule, **static_charges}


def build_energy_schedule_raw(df: pl.DataFrame, location_avg_factor: float, taxes: list[float]) -> URDBRate:
    date_columns = _extract_date_columns(df)
    month_bands: list[tuple[tuple[float, float], ...]] = []
    for month in range(0, 12):
        bands = [
            (
                _row_min_kwh(row),
                _row_max_kwh(row),
                _row_rate_kwh(row, date_columns[month])
                * (location_avg_factor if row.get("location") else 1)
                * taxes[month],
            )
            for row in cast(Iterable[Row], df.iter_rows(named=True))
            if _is_consumption_rate(row)
        ]
        # Sum bands
        band_limits = sorted({*(l1 for l1, _, _ in bands), *(l2 for _, l2, _ in bands)})
        print(band_limits)
        summed_bands = tuple(
            (limit, sum(rate for low, high, rate in bands if low < limit <= high)) for limit in band_limits
        )
        # round bands
        summed_bands = tuple(
            (round(limit) if limit != inf else inf, round(max(0, value), 6)) for limit, value in summed_bands
        )
        # join bands
        summed_bands = [
            *(this for this, next_ in itertools.pairwise(summed_bands) if this[1] != next_[1] and this[0] != 0),
            summed_bands[-1],
        ]
        # remove <30kwh difference bands
        # Most bands on rateacuity are in therms or ccf, which causes small gaps
        # when converting them to kwh, so this way we attempt to circumvent this.
        # It's not ideal but will do for now
        summed_bands = [
            summed_bands[0],
            *(this for prev, this in itertools.pairwise(summed_bands) if this[0] - prev[0] > 30),
        ]
        month_bands.append(tuple(summed_bands))

    month_bands_unique = list(set(month_bands))
    energy_weekday_schedule = cast(MonthSchedule, tuple(tuple([month_bands_unique.index(b)] * 24) for b in month_bands))
    energy_weekend_schedule = energy_weekday_schedule
    energy_rate_structure = [[_band_tuple_to_tier(br) for br in mb if br != (0, 0)] for mb in month_bands_unique]
    return {
        "energyratestructure": energy_rate_structure,
        "energyweekdayschedule": energy_weekday_schedule,
        "energyweekendschedule": energy_weekend_schedule,
    }


def _build_static_charges(df: pl.DataFrame, location_avg_factor: float) -> URDBRate:
    date_columns = _extract_date_columns(df)
    fixed_charge_sum = (
        sum(
            (cast(float, row[date_columns[month]] or 0)) * (location_avg_factor if row.get("location") else 1)
            for row in cast(Iterable[Row], df.iter_rows(named=True))
            for month in range(0, 12)
            if _is_fixed_rate(row)
        )
        / 12
    )
    return {"fixedchargefirstmeter": fixed_charge_sum, "fixedchargeunits": "$/month"}


def _get_average_month_tax(df: pl.DataFrame, location_avg_factor: float) -> list[float]:
    date_columns = _extract_date_columns(df)
    return [
        1.0
        + mean(
            [
                value
                for row in cast(Iterable[Row], df.iter_rows(named=True))
                if _is_percentage_rate(row)
                if (value := cast(float | None, row[date_columns[month]])) is not None
            ]
            or [0]
        )
        / 100
        for month in range(0, 12)
    ]


def _get_location_avg_factor(df: pl.DataFrame) -> float:
    num_locations = len({_.get("location") for _ in df.iter_rows(named=True) if _.get("location")})
    if num_locations == 0:
        return 1
    return 1 / num_locations


def _band_tuple_to_tier(band_tuple: tuple[float, float]) -> EnergyTier:
    limit, rate = band_tuple
    if limit == inf:
        return {"rate": rate, "unit": "kWh"}
    return {"rate": rate, "unit": "kWh", "max": limit}


def _extract_date_columns(df: pl.DataFrame) -> list[str]:
    date_columns = [col for col in df.columns if _DATE_COL_RE.match(col)]
    date_columns = sorted(date_columns, key=lambda c: datetime.strptime(c, "%m/%d/%Y").month)
    date_columns_datetimes = [datetime.strptime(c, "%m/%d/%Y") for c in date_columns]
    if [c.month for c in date_columns_datetimes] != list(range(1, 13)):
        raise IncorrectDataframeSchemaMonths()
    if len({c.year for c in date_columns_datetimes}) != 1:
        raise IncorrectDataframeSchemaMultipleYears()
    return date_columns


def validate_dataframe(df: pl.DataFrame) -> list[str]:
    df_schema = df.schema
    non_date_columns = {col for col in df_schema if not _DATE_COL_RE.match(col)}
    result: list[str] = []

    allow_empty_columns = non_date_columns - set(KNOWN_COLUMNS)
    non_empty_columns = [
        c
        for c in allow_empty_columns
        if not (df[c].is_null() | (df[c] == "" if df[c].dtype == pl.Utf8 else False)).all()
    ]

    if non_empty_columns:
        result.append(f"Conversion logic is undefined for these non-empty columns: {non_empty_columns}")

    known_rate_determinants = set(get_args(KnownRateDeterminant))
    unknown_rate_determinants = cast(
        list[str],
        (df["rate_determinant"].filter(~df["rate_determinant"].is_in(known_rate_determinants)).unique().to_list()),
    )
    if unknown_rate_determinants:
        result.append(
            f"Found following unknown rate determinants: {unknown_rate_determinants}. These rates will be ignored."
        )

    if "determinant" in df_schema:
        band_determinants = set(get_args(BandDeterminant))
        unknown_band_determinants = cast(
            list[str],
            (df["determinant"].filter(~df["determinant"].is_in(band_determinants)).unique().to_list()),
        )
        if unknown_band_determinants:
            result.append(
                f"Found unknown band determinants: {unknown_band_determinants}. These limits will be ignored."
            )

    return result


def _row_min_kwh(row: Row) -> float:
    determinant = row.get("determinant")
    if determinant is None:
        return 0
    if determinant not in get_args(BandDeterminant):
        return 0
    if (start := row["start"]) is not None:
        return round(start * _kwh_multiplier(determinant))

    return 0


def _row_max_kwh(row: Row) -> float:
    determinant = row.get("determinant")
    if determinant is None:
        return inf
    if determinant not in get_args(BandDeterminant):
        return inf
    if (end := row["end"]) is not None:
        return round(end * _kwh_multiplier(determinant))
    return inf


def _row_rate_kwh(row: Row, column: str) -> float:
    rate_determinant = row["rate_determinant"]
    if not _is_consumption_rate(row):
        return 0
    column_value = cast(float | None, row.get(column))
    if column_value is None:
        return 0
    return column_value / _kwh_multiplier(cast(ConsumptionRateDeterminant, rate_determinant))


def _kwh_multiplier(determinant: ConsumptionRateDeterminant | BandDeterminant) -> float:
    match determinant:
        case "per therm" | "therms":
            return 29.3
        case "per ccf" | "ccf":
            return 29.31


def _is_consumption_rate(row: Row):
    rate_determinant = row["rate_determinant"]
    return rate_determinant in get_args(ConsumptionRateDeterminant)


def _is_percentage_rate(row: Row) -> bool:
    determinant = row["rate_determinant"]
    return determinant in get_args(PercentRateDeterminant)


def _is_fixed_rate(row: Row) -> bool:
    determinant = row["rate_determinant"]
    return determinant in get_args(FixedRateDeterminant)


def _is_correct_rate_determinant(determinant: str) -> TypeIs[RateDeterminant]:
    return determinant in get_args(RateDeterminant)
