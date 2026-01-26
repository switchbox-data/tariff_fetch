from typing import Annotated, TypedDict

from pydantic import Field
from pydantic.alias_generators import to_camel

from tariff_fetch.genability.schema.season import SeasonExtended, SeasonStandard

from .common import TimeOfUsePrivacy, TimeOfUseType


class Period(TypedDict):
    tou_period_id: int
    """The unique Arcadia ID of this period. This is unique across all LSE's."""
    tou_id: int
    """The ID of the parent time of use this period belongs to (foreign key)."""
    from_day_of_week: Annotated[int, Field(ge=0, le=6)]
    """The day of the week this period starts. 0-6 Monday-Sunday."""
    from_hour: Annotated[int, Field(ge=0, le=23)]
    """The hour this period starts. 0-23."""
    from_minute: Annotated[int, Field(ge=0, le=59)]
    """The minute this period starts. 0-59."""
    to_day_of_week: Annotated[int, Field(ge=0, le=6)]
    """The day of the week this period ends. 0-6 Monday-Sunday."""
    to_hour: Annotated[int, Field(ge=0, le=23)]
    """The hour this period ends. 0-23."""
    to_minute: Annotated[int, Field(ge=0, le=59)]
    """The minute this period ends. 0-59."""
    calendar_id: int | None


class TimeOfUseStandardFields(TypedDict):
    tou_id: int
    """Unique Arcadia ID (primary key) for each time of use. This is unique across all LSEs."""
    tou_group_id: int
    """Associates the rate with a tariff (foreign key)"""
    lse_id: int
    """ID of load serving entity this time of use group belongs to"""
    tou_name: str
    """Display name of this TOU. Example: "On Peak" """
    calendar_id: int | None
    """The ID of the calendar of events and holidays that this TOU should apply to, regardless of the TOU period definitions.

    For example, a calendar could be used to specify that the entirety of Labor Day should be treated as OFF_PEAK,
        even though it falls on a Summer weekday.
    """
    tou_type: TimeOfUseType
    is_dynamic: bool
    """Indicates if the timeOfUse includes a calendar whose dates change from year to year.

    For example Critical Peak timeOfUse objects are dynamic, since the dates/hours change from year to year.
    """
    tou_periods: list[Period]
    """	The periods that comprise this time of use."""


class TimeOfUseExtendedFields(TypedDict):
    privacy: TimeOfUsePrivacy
    """Indicates whether this TimeOfUse is PUBLIC or PRIVATE. Only TOU groups created by your organization will be returned as PRIVATE."""


class TimeOfUseStandard(TimeOfUseStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    season: SeasonStandard | None


class TimeOfUseExtended(TimeOfUseStandardFields, TimeOfUseExtendedFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    season: SeasonExtended | None
