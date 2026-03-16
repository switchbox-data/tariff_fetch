from typing import Annotated, Literal

from pydantic import BeforeValidator
from pydantic.alias_generators import to_camel
from typing_extensions import TypedDict

from .validators import comma_separated_str

OfferingType = Literal["Bundle", "Delivery", "Energy"]
Ownership = Literal[
    "INVESTOR",
    "COOP",
    "MUNI",
    "FEDERAL",
    "POLITICAL_SUBDIVISION",
    "RETAIL_ENERGY_MARKETER",
    "WHOLESALE_ENERGY_MARKETER",
    "TRANSMISSION",
    "STATE",
    "UNREGULATED",
]
ServiceType = Literal["ELECTRICITY", "SOLAR_PV"]


class BillingPeriodRepresentation(TypedDict):
    from_date_offset: int
    """The number of days to add to a Arcadia-style fromDate to obtain the LSE's start of a billing period."""
    to_date_offset: int
    """The number of days to add to a Arcadia-style toDate to obtain the LSE's end of a billing period."""
    style: str
    """Arcadia name for this particular style of a Billing Period Representation."""


class LSEMinimalFields(TypedDict):
    lse_id: int
    """Unique Arcadia ID (primary key) for each LSE"""
    name: str
    """Published name of the company"""
    code: str
    """Shortcode (an alternate key). For US companies this is the EIA ID"""
    website_home: str
    """The URL to the home page of the LSE website"""


class LSEExtendedFields(TypedDict):
    lse_code: str
    offering_type: OfferingType
    """Utility classification is based on the type of service they offer.

    Possible values:
        Bundled - The utility provides all the electricity services bundled into one, including the transportation (transmission and distribution) and the generation (energy) portion.
        Delivery - Responsible for the transportation (transmission and distribution) of power only.
        Energy - Provides only the generation (energy) portion of the service. Energy Suppliers are sometimes referred to as Retail Energy Providers.
    """
    ownership: Ownership
    """Ownership structure"""
    service_types: Annotated[list[ServiceType], BeforeValidator(comma_separated_str)]
    totalRevenues: int
    totalSales: int
    totalCustomers: int
    residential_service_types: Annotated[list[ServiceType], BeforeValidator(comma_separated_str)] | None
    residential_revenues: int
    residential_sales: int
    residential_customers: int
    commercial_service_types: Annotated[list[ServiceType], BeforeValidator(comma_separated_str)] | None
    commercial_revenues: int
    commercial_sales: int
    commercial_customers: int
    industrial_service_types: Annotated[list[ServiceType], BeforeValidator(comma_separated_str)] | None
    industrial_revenues: int
    industrial_sales: int
    industrial_customers: int
    transportation_service_types: Annotated[list[ServiceType], BeforeValidator(comma_separated_str)] | None
    transportation_revenues: int
    transportation_sales: int
    transportation_customers: int
    billing_period_representation: BillingPeriodRepresentation


class LSEMinimal(LSEMinimalFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class LSEExtended(LSEMinimalFields, LSEExtendedFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
