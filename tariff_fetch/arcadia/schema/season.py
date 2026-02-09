from typing import Annotated, NotRequired, TypedDict

from pydantic import Field
from pydantic.alias_generators import to_camel

from .common import SeasonPredominance


class SeasonStandardFields(TypedDict):
    season_id: int
    """Unique Arcadia ID (primary key) for each season"""
    lse_id: int
    """The ID of the LSE this territory belongs to"""
    season_group_id: int
    """The ID of the season group that contains this season"""
    season_name: str
    """The name of the season (i.e. "Summer" or "Winter")"""
    season_from_month: Annotated[int, Field(ge=1, le=12)]
    """	Value of 1-12 representing the month this season begins"""
    season_from_day: Annotated[int, Field(ge=1, le=31)]
    """Value of 1-31 (depending on month) representing the day this season begins"""
    season_to_month: Annotated[int, Field(ge=1, le=12)]
    """Value of 1-12 representing the month this season ends"""
    season_to_day: Annotated[int, Field(ge=1, le=31)]
    """Value of 1-31 (depending on month) representing the day this season ends"""


class SeasonExtendedFields(TypedDict):
    from_edge_predominance: NotRequired[SeasonPredominance | None]
    """
    Can be None (from date is a fixed date),
    PREDOMINANT (from date is the start of the bill the season starts in),
    or SUBSERVIENT (from date is the end of the bill the season starts in).
    """
    to_edge_predominance: NotRequired[SeasonPredominance | None]
    """
	Can be None (to date is a fixed date),
    PREDOMINANT (to date is the start of the bill the season starts ends in),
    or SUBSERVIENT (to date is the end of the bill the season starts in).
    """


class SeasonStandard(SeasonStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class SeasonExtended(SeasonStandardFields, SeasonExtendedFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
