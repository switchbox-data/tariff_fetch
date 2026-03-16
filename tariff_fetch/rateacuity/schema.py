import re
from datetime import date
from typing import Annotated, Any, Generic, Literal, NamedTuple, TypeVar

from pydantic import BeforeValidator, Field
from pydantic.alias_generators import to_camel
from typing_extensions import TypedDict

USStateCode = Literal[
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
]

UseType = Literal["C", "R", "I", "A", " "]
"""
Indicator of what type of customer accounts the schedule can be used for.
C=Commercial, R=Residential, I=Industrial, A=Agricultural. Will be blank if used for
more than one type of account.
"""

SCRateDeterminant = Literal["per month"]
OCRateDeterminant = Literal["per month"]
CORateDeterminant = Literal["per therm"]


class MonthAndDay(NamedTuple):
    month: int
    day: int


def month_and_day(input_: str | MonthAndDay | None) -> MonthAndDay | None:
    if input_ is None:
        return None
    if isinstance(input_, tuple):
        return input_
    daystr, monthstr = input_.split("-")
    return MonthAndDay(
        month=("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC").index(
            monthstr.upper()
        ),
        day=int(daystr),
    )


def empty_is_none(input_: Any) -> str | None:  # pyright: ignore[reportAny, reportExplicitAny]
    if not isinstance(input_, str):
        return input_  # pyright: ignore[reportAny]
    if not input_:
        return None
    return input_


empty_or_none_validator = BeforeValidator(empty_is_none)
FloatOrNone = Annotated[float | None, empty_or_none_validator]
DateOrNone = Annotated[date | None, empty_or_none_validator]
StrOrNone = Annotated[str | None, empty_or_none_validator]

MonthAndDayAnnotated = Annotated[MonthAndDay, BeforeValidator(month_and_day)]
MonthAndDayOrNone = Annotated[MonthAndDay | None, BeforeValidator(month_and_day), empty_or_none_validator]


def to_spaced_camel(snake_case: str) -> str:
    camel = to_camel(snake_case)  # snake_case -> lowerCamelCase
    spaced = re.sub(r"([A-Z])", r" \1", camel)
    return spaced.strip().title()


class Schedule(TypedDict):
    __pydantic_config__ = {"alias_generator": to_spaced_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    state: USStateCode
    utility: str
    schedule_name: str
    schedule_description: str
    use_type: UseType
    min_peak: FloatOrNone
    """ Start of specific peak range for which the schedule should be used """
    max_peak: FloatOrNone
    """End of specific peak range for which the schedule should be used"""
    peak_determinant: str
    """Used in conjunction with MinPeak and MaxPeak to define the unit of measure for peak values"""
    min_usage: FloatOrNone
    """Indicator of minimum usage of account served by the schedule"""
    max_usage: FloatOrNone
    """Indicator of maximum usage of account served by the schedule"""
    usage_determinant: str
    """Used in conjunction with MinUsage and MaxUsage to define the min and max measurement"""
    option_description: str
    """Text description of specific option from tariff for this data set"""
    load_season: str
    """
    If the schedule is applicable based on load during a specific season the season is shown here
    """
    load_comp: str
    """
    If the schedule is applicable on load during a specific season compared to
    other months, the months to compare are shown here
    """
    load_percent: FloatOrNone
    """
    If the schedule is applicable on load during a specific season compared to
    other months, the comparison value is shown here
    """
    season_start: DateOrNone
    """First date of season"""
    season_end: DateOrNone
    """Last date of season"""
    effective_date: date


class ServiceCharge(TypedDict):
    __pydantic_config__ = {"alias_generator": to_spaced_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    service_charges: str
    season_start: DateOrNone
    season_end: DateOrNone
    start: FloatOrNone
    """The minimum value for which this record should be used"""
    end: FloatOrNone
    """The maximum value for which this record should be used"""
    charge_determinant: str
    """Used with Start and End to show the measurement of the values of
    these fields"""
    rate: float
    rate_determinant: SCRateDeterminant
    """Measure of rate charge"""
    effective_date: date


class OtherCharge(TypedDict):
    __pydantic_config__ = {"alias_generator": to_spaced_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    other_charges: str
    rate: float
    rate_determinant: OCRateDeterminant
    min_therms: FloatOrNone
    max_therms: FloatOrNone
    effective_date: date


class Consumption(TypedDict):
    __pydantic_config__ = {"alias_generator": to_spaced_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    consumption: str
    season_start: MonthAndDayOrNone
    season_end: MonthAndDayOrNone
    rate: float
    rate_determinant: CORateDeterminant
    effective_date: date


T = TypeVar("T")


class Table(TypedDict, Generic[T]):
    title: str
    values: Annotated[list[T], Field(fail_fast=True)]


ScheduleTable = Table[Schedule]
ServiceChargesTable = Table[ServiceCharge]
OtherChargesTable = Table[OtherCharge]
ConsumptionTable = Table[Consumption]

TableUnion = ScheduleTable | ServiceChargesTable | OtherChargesTable | ConsumptionTable


class Section(TypedDict):
    section: str | None
    tables: Annotated[list[TableUnion], Field(fail_fast=True)]


class Tariff(TypedDict):
    schedule: str
    sections: list[Section]
