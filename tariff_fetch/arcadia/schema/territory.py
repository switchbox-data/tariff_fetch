from typing import NotRequired

from pydantic.alias_generators import to_camel
from typing_extensions import TypedDict

from .common import TerritoryItemType, TerritoryUsageType


class Coordinate(TypedDict):
    latitude: float
    longitude: float


class TerritoryItem(TypedDict):
    territory_item_id: int
    """	Unique Arcadia ID (primary key) for each territory Item"""
    territory_type: TerritoryItemType
    value: str
    """The name of the territory item (i.e. 'Kirkwood' or '94115')."""
    exclude: bool
    """If True, this territory item is not included as part of the coverage area of the parent territory."""
    partial: bool
    """If True, then only a partial area of this territory item is covered by this LSE."""


class TerritoryLSE(TypedDict):
    territory_id: int
    """	The territoryId this Territory LSE belongs to"""
    lse_id: int
    """The lseId of the LSE offering service in this Territory"""
    lse_name: str
    """The name of the LSE"""
    distribution: bool
    """indicates whether this LSE is a distribution LSE"""
    supplier_residential: bool
    """indicates whether this LSE supplies service to residential customers"""
    supplier_general: bool
    """indicates whether this LSE supplies service to general (commercial and industrial) customers"""
    residential_coverage: float
    """Percentage of residential customers this LSE supplies service to"""
    general_coverage: float
    """Percentage of general (commercial and industrial) customers this LSE supplies service to"""


class TerritoryMinimalFields(TypedDict):
    territory_id: int
    """Unique Arcadia ID (primary key) for each territory"""
    territory_name: str
    """The name of the territory (i.e. 'Service Area for CA' or 'Baseline Region H')."""
    lse_id: int
    """The ID of the LSE this Territory belongs to"""
    lse_name: str
    """The name of the LSE (utility) that this territory belongs to."""
    country_code: str


class TerritoryStandardFields(TypedDict):
    parent_territory_id: int | None
    """The ID of the parent territory

    Typically this will be on a tariff territory that ties it back to the service territory.
    """
    usage_type: TerritoryUsageType
    """The type of the items that define the physical area of coverage of this territory"""
    item_types: TerritoryItemType
    items: NotRequired[list[TerritoryItem]]
    """The list of Territory Items that define the area covered by this territory."""
    territory_lses: NotRequired[list[TerritoryLSE]]
    """	The list of LSEs that offer service (retail) to customers in this territory. Applies to deregulated markets."""
    dereg_res: bool
    """Whether the residential electricity market in this territory is deregulated."""
    dereg_candi: bool
    """	Whether the commercial and industrial electricity market in this territory is deregulated."""
    center_point: Coordinate
    """	The latitude and longitude of the centerPoint of this territory."""


class TerritoryMinimal(TerritoryMinimalFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class TerritoryStandard(TerritoryMinimalFields, TerritoryStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
