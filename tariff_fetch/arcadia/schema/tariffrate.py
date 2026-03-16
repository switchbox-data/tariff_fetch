from datetime import datetime
from typing import Annotated, NotRequired

from pydantic import BeforeValidator
from pydantic.alias_generators import to_camel
from typing_extensions import TypedDict

from .common import RateChargeClass, RateTransactionType, RateUnit, TariffChargePeriod, TariffChargeType
from .season import SeasonExtended, SeasonStandard
from .territory import TerritoryStandard
from .timeofuse import TimeOfUseExtended, TimeOfUseStandard
from .validators import comma_separated_str


class TariffRateBand(TypedDict):
    tariff_rate_band_id: int
    """Unique Arcadia ID (primary key) for each Band"""
    tariff_rate_id: int
    """ID of the rate this band belongs to (foreign key)"""
    rate_sequence_number: int
    """This bands position in the bands for its rate"""
    has_consumption_limit: bool
    """True indicates that this has banded consumption"""
    consumption_upper_limit: NotRequired[float]
    """indicates the upper consumption limit of this band"""
    has_demand_limit: bool
    """True indicates that this has banded demand"""
    demand_upper_limit: NotRequired[float]
    """indicates the upper demand limit of this band"""
    has_property_limit: bool
    """true indicates that this has a limit based on a property"""
    property_upper_limit: NotRequired[float]
    """indicates the upper limit of this band"""
    prev_upper_limit: float | None
    """The upper limit of the previous rate band for this rate"""
    applicability_value: NotRequired[str]
    """indicates the value of applicability property that qualifies for this rate"""
    calculation_factor: NotRequired[float]
    """A factor to be applied to the cost of the rate."""
    rate_amount: float
    """Charge amount for this band"""
    rate_unit: RateUnit
    """
    Possible values are:

    COST_PER_UNIT - rate amount multiplied by the number of units
    PERCENTAGE - percentage of a value (e.g. percentage of overall bill)
    """
    is_credit: bool
    """When true this band is a credit amount (reduces the bill)"""
    applicability_formula: NotRequired[str]


class TariffRateMinimalFields(TypedDict):
    master_tariff_rate_id: int | None
    has_applicability_formula: bool
    tariff_rate_id: int
    """Unique Arcadia ID (primary key) for each tariff rate"""
    tariff_id: int
    """Associates the rate with a tariff (foreign key)"""
    rider_id: NotRequired[int]
    """Tariff ID of the rider attached to this tariff version."""
    tariff_sequence_number: int
    """Sequence of this rate in the tariff, for display purposes only (e.g. this is the order on the bill)"""
    rate_group_name: str
    """Name of the group this rate belongs to"""
    rate_name: str | None
    """Name of this rate. If None, `rate_group_name` is used."""


class TariffRateStandardFields(TypedDict):
    from_date_time: datetime | None
    """Indicates the rate's effective date is not the same as that of its tariff"""
    to_date_time: datetime | None
    """Indicates the rates end date is not the same as that of its tariff"""
    charge_type: TariffChargeType | None
    """
    Possible values are:
        FIXED_PRICE - a fixed charge for the period
        CONSUMPTION_BASED - based on quantity used (e.g. kW/h)
        DEMAND_BASED - based on the peak demand (e.g. kW)
        QUANTITY - a rate per number of items (e.g. $5 per street light)
        FORMULA - a rate that has a specific or custom formula
        MINIMUM - a minimum amount that the LSE will charge you, overriding lower pre-tax charges
        MAXIMUM - a maximum amount that the LSE will charge you, overriding higher pre-tax charges
        TAX - a percentage tax rate which is applied to the sum of all of the other charges on a bill
    """
    charge_class: NotRequired[Annotated[list[RateChargeClass], BeforeValidator(comma_separated_str)]]
    """indicates what class(es) of charges this rate is for.

    Values include:
        SUPPLY - Energy-related charges.
        TRANSMISSION - Transmission level delivery charges.
        DISTRIBUTION - Distribution level (last mile) delivery charges of moving electricity into your home or business.
        TAX - Tax surcharges that appear in the utility tariff document.
        CONTRACTED - Charges that get replaced or overridden when you pass the retail (contracted) energy supply rate in the calculation.
        USER_ADJUSTED - Additional or custom rates you can add to a public or private tariff.
            An example would be a local tax rate which Arcadia does not model but you would want included.
        AFTER_TAX - Charges which apply post utility and other taxes.
            A good example would be the California Climate credit which is applied to the bill after the taxes are applied to the bill subtotal.
        OTHER - Charges which cannot be classified in any of the above buckets. This is very rare.
        NON_BYPASSABLE - Charges which cannot be offset by credits (usually Net Metering)
    """
    charge_period: TariffChargePeriod
    """
    Indicates what period this charge is calculated for.
    This is usually the same as the billing period (and is usually monthly) but can be other intervals.
    """
    quantity_key: NotRequired[str | None]
    """ When not null, the property that defines the type of quantity this rate applies to.
        (e.g. billingMeter : property which defines the number of billing meters the rate will apply to)
    """
    applicability_key: NotRequired[str]
    """ defines the eligibility criteria for this rate. (e.g. connectionType : property which defines how the service is connected to the grid) """
    variable_limit_key: NotRequired[str]
    """defines the variable which determines the upper limit(s) of this rate

    e.g. demandMultiplierTierswithkWhTiers2416: property which uses the demand value to drive the consumption limits
    """
    variable_rate_key: NotRequired[str]
    variable_rate_sub_key: NotRequired[str]
    """this is the name of the property that defines the variable rate

    e.g massachusettsResidentialRetailPrevailingRates : property which provides the regional prevailing residential supply rate for Massachusetts
    """
    variable_factor_key: NotRequired[str]
    """The name of the property that defines the variable factor to apply to this rate.

    e.g billingPeriodProrationFactor: property which defines a prorated number of billing days
    """
    rate_bands: list[TariffRateBand]

    # These are fields with unknown purpose
    edge_predominance: NotRequired[str]
    proration_rules: NotRequired[list[str]]


class TariffRateExtendedFields(TypedDict):
    rider_tariff_id: NotRequired[int]
    """Tariff ID of the rider attached to this tariff version. """
    tariff_book_sequence_number: int | None
    """Sequence of this rate in the tariff source document, if it differs from tariff_sequence_number"""
    tariff_book_rate_group_name: str | None
    """Name of the group this rate belongs to in the tariff source document, if it differs from rate_group_name"""
    tariff_book_rate_name: str | None
    """Name of this rate in the tariff source document, if it differs from rate_name"""
    transaction_type: RateTransactionType
    """
    Indicates whether this rate is BUY (charge when importing from the grid, no credit when exporting),
    SELL (credit when exporting to the grid, no charge when importing),
    or NET (charge when importing, credit when exporting) with imports and exports resolved according the the chargePeriod.
    BUY_IMPORT (charge only when importing) and
    SELL_EXPORT (credit only when exporting) indicate that imports and exports are resolved in real-time
    (instantaneous netting).
    """


class TariffRateMinimal(TariffRateMinimalFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class TariffRateStandard(TariffRateMinimalFields, TariffRateStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    time_of_use: NotRequired[TimeOfUseStandard]
    """The time period this rate applies to. Only used for TOU rates"""
    territory: NotRequired[TerritoryStandard]
    """Only populated when this rate applies to a different region than the whole tariff (e.g. California Baseline Regions)."""
    season: NotRequired[SeasonStandard]
    """The season this rate applies to. Only used for seasonal rates"""


class TariffRateExtended(TariffRateMinimalFields, TariffRateStandardFields, TariffRateExtendedFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    time_of_use: NotRequired[TimeOfUseExtended]
    """The time period this rate applies to. Only used for TOU rates"""
    territory: NotRequired[TerritoryStandard]
    """Only populated when this rate applies to a different region than the whole tariff (e.g. California Baseline Regions)."""
    season: NotRequired[SeasonExtended]
    """The season this rate applies to. Only used for seasonal rates"""
