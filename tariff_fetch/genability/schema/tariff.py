from datetime import date, datetime
from typing import Annotated, NotRequired, TypedDict

from pydantic import BeforeValidator, FailFast
from pydantic.alias_generators import to_camel

from .common import (
    CustomerClass,
    TariffChargePeriod,
    TariffChargeType,
    TariffEffectiveOnRule,
    TariffPrivacy,
    TariffServiceType,
    TariffType,
)
from .tariffproperty import TariffPropertyStandard
from .tariffrate import TariffRateExtended, TariffRateStandard


class TariffStandardFields(TypedDict):
    prior_tariff_id: int
    "Unique Arcadia ID that identifies the prior revision of the tariffId above"
    distribution_lse_id: NotRequired[int | None]
    """
    In states like Texas where the load-serving entity that sells the power is
    different than the load-serving entity that distributes the power, this will
    contain the ID of the distribution LSE. Otherwise, it will be None.
    """
    tariff_type: TariffType
    """
    Possible values are:
      DEFAULT - tariff that is automatically given to this service class
      ALTERNATIVE - opt-in alternate tariff for this service class
      OPTIONAL_EXTRA - opt-in extra, such as green power or a smart thermostat program
      RIDER - charge that can apply to multiple tariffs. Often a regulatory-mandated charge
    """
    customer_class: CustomerClass
    """
    Possible values are:
      RESIDENTIAL - homes, apartments etc.
      GENERAL - commercial, industrial, and other business and organization service types
        (often have additional applicability criteria)
      SPECIAL_USE - examples are government, agriculture, street lighting, transportation
      PROPOSED - Utility rates that have been proposed by utilities and approved by utility commissions,
        but are not yet effective (requires product subscription)
    """
    customer_count: int
    "Number of customers that are on this master tariff"
    """
    The likelihood that a customer is on this tariff of all the tariffs in the search results.
    """
    customer_likelihood: NotRequired[float]
    """
    The likelihood that a customer is on this tariff of all the tariffs in the search results.
    Only populated when getting more than one tariff.
    """
    territory_id: int
    """
    ID of the territory that this tariff applies to.
    This is typically the service area for the LSE in this regulatory region (i.e. a state in the USA)
    """
    effective_date: date
    "Date on which this tariff is no longer effective. Can be null which means end date is not known or tariff is open-ended"
    end_date: date | None
    "Date on which the tariff was or will be effective"
    time_zone: str
    "If populated (usually is), it's the timezone that this tariffs dates and times refer to"
    effective_on_rule: TariffEffectiveOnRule
    billing_period: str
    "How frequently bills are generated."
    currency: str
    "ISO Currency code that the rates for this tariff refer to (e.g. USD for USA Dollar)"
    charge_types: Annotated[
        list[TariffChargeType], BeforeValidator(lambda _: _.split(",") if isinstance(_, str) else _)
    ]
    "List of all the different ChargeType rates on this tariff"
    charge_period: TariffChargePeriod
    "The most fine-grained period for which charges are calculated."
    has_time_of_use_rates: bool
    "Indicates whether this tariff contains one or more Time of Use Rate."
    has_tiered_rates: bool
    "Indicates whether this tariff contains one or more Tiered Rate."
    has_contracted_rates: bool
    """
    Indicates whether this tariff contains one or more Rate that can be contracted
    (sometimes called by-passable or associated with a price to compare).
    """
    has_rate_applicability: bool
    """
    Indicates that one or more rates on this tariff are only applicable to customers with a particular circumstance.
    When true, this will be specified in the TariffProperty collection, and also on the TariffRate or rates in question.
    """


class TariffExtendedFields(TypedDict):
    tariff_book_name: str
    "Name of the tariff as it appears in the tariff document"
    lse_code: str
    "Abbreviated name of the load-serving entity"
    customer_count_source: str
    "Where we got the customer count numbers from. Typically FERC (form 1 filings) or Arcadia (our own estimates)."
    closed_date: datetime | None
    """
    Date on which a tariff became closed to new customers,
    but still available for customers who were on it at the time.
    Can be null which means that the tariff is not closed.
    All versions of a particular tariff
    (i.e. those that share a particular masterTariffId)
    will have the same closedDate value.
    """
    min_monthly_consumption: float | None
    "When applicable, the minimum monthly consumption allowed to be eligible for this tariff."
    "When applicable, the maximum monthly consumption allowed to be eligible for this tariff."
    max_monthly_consumption: float | None
    "When applicable, the minimum monthly demand allowed to be eligible for this tariff."
    min_monthly_demand: float | None
    "When applicable, the maximum monthly demand allowed to be eligible for this tariff."
    max_monthly_demand: float | None
    "Indicates that this tariff has additional eligibility criteria, as specified in the TariffProperty collection"
    has_tariff_applicability: bool
    has_net_metering: bool
    "Indicates whether this tariff contains one or more net metered rates."
    privacy: TariffPrivacy
    "Privacy status of the tariff."


class TariffMinimalFields(TypedDict):
    is_active: bool

    tariff_id: int
    "Unique Arcadia ID (primary key) for this tariff"
    master_tariff_id: int
    "Unique Arcadia ID that persists across all revisions of this tariff"
    tariff_code: str
    "Shortcode that the LSE uses as an alternate name for the tariff"
    tariff_name: str
    "Name of the tariff as used by the LSE"
    lse_id: int
    "ID of load serving entity this tariff belongs to"
    lse_name: str
    "Name of the load-serving entity"
    service_type: TariffServiceType
    "Type of service for the tariff"


class TariffMinimal(TariffMinimalFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class TariffStandard(TariffMinimalFields, TariffStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    properties: NotRequired[list[TariffPropertyStandard]]
    rates: NotRequired[list[TariffRateStandard]]


class TariffExtended(TariffMinimalFields, TariffStandardFields, TariffExtendedFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "forbid"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    properties: NotRequired[list[TariffPropertyStandard]]
    rates: NotRequired[Annotated[list[TariffRateExtended], FailFast()]]


Tariff = TariffMinimal | TariffStandard | TariffExtended
