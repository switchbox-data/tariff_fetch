from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, NewType, TypeAlias, TypedDict

from typing_extensions import NotRequired, Required


def api_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d")


TariffRateExtended = NewType("TariffRateExtended", dict)
TariffRateStandard = NewType("TariffRateStandard", dict)
TariffDocumentExtended = NewType("TariffDocumentExtended", dict)
TariffDocumentStandard = NewType("TariffDocumentStandard", dict)
TariffDocumentMinimal = NewType("TariffDocumentMinimal", dict)
Territory = NewType("Territory", dict)
Season = NewType("Season", dict)
TimeOfUse = NewType("TimeOfUse", dict)


LoadServingOfferingType: TypeAlias = Literal["Bundle"] | Literal["Bundled"] | Literal["Delivery"] | Literal["Energy"]
LoadServingOwnership: TypeAlias = (
    Literal["INVESTOR"]
    | Literal["COOP"]
    | Literal["MUNI"]
    | Literal["FEDERAL"]
    | Literal["POLITICAL_SUBDIVISION"]
    | Literal["RETAIL_ENERGY_MARKETER"]
    | Literal["WHOLESALE_ENERGY_MARKETER"]
    | Literal["TRANSMISSION"]
    | Literal["STATE"]
    | Literal["UNREGULATED"]
)
LoadServingServiceType: TypeAlias = Literal["ELECTRICITY"] | Literal["SOLAR_PV"]
BillingPeriodStyle: TypeAlias = Literal[
    "ArcadiaStyle", "InclusiveToDate", "ExclusiveFromDateAndInclusiveToDate", "Unknown"
]

TariffType: TypeAlias = Literal["DEFAULT"] | Literal["ALTERNATIVE"] | Literal["OPTIONAL_EXTRA"] | Literal["RIDER"]
TariffServiceType: TypeAlias = LoadServingServiceType | Literal["GAS"]
TariffPrivacy: TypeAlias = Literal["PUBLIC", "UNLISTED", "PRIVATE"]
TariffEffectiveOnRule: TypeAlias = Literal["TARIFF_EFFECTIVE_DATE", "BILLING_PERIOD_START"]
TariffChargeType: TypeAlias = Literal[
    "FIXED_PRICE",
    "CONSUMPTION_BASED",
    "DEMAND_BASED",
    "QUANTITY",
    "FORMULA",
    "MINIMUM",
    "MAXIMUM",
    "TAX",
]
TariffChargeClass: TypeAlias = Literal[
    "SUPPLY",
    "TRANSMISSION",
    "DISTRIBUTION",
    "TAX",
    "CONTRACTED",
    "USER_ADJUSTED",
    "AFTER_TAX",
    "OTHER",
    "NON_BYPASSABLE",
]
TariffChargePeriod: TypeAlias = Literal["MONTHLY", "DAILY", "QUARTERLY", "ANNUALLY"]
TariffTransactionType: TypeAlias = Literal["BUY", "SELL", "NET", "BUY_IMPORT", "SELL_EXPORT"]
TariffPropertyPeriod: TypeAlias = Literal["ON_PEAK", "PARTIAL_PEAK", "OFF_PEAK", "CRITICAL_PEAK"]
TariffPropertyDataType: TypeAlias = Literal[
    "string",
    "choice",
    "boolean",
    "date",
    "decimal",
    "integer",
    "formula",
    "demand",
    "STRING",
    "CHOICE",
    "BOOLEAN",
    "DATE",
    "DECIMAL",
    "INTEGER",
    "FORMULA",
    "DEMAND",
]
TariffPropertyCategory: TypeAlias = Literal[
    "APPLICABILITY", "RATE_CRITERIA", "BENEFIT", "DATA_REPUTATION", "SERVICE_TERMS"
]
TariffRateBandUnit: TypeAlias = Literal["COST_PER_UNIT", "PERCENTAGE"]
CustomerClass = Literal["RESIDENTIAL"] | Literal["GENERAL"] | Literal["SPECIAL_USE "]
TariffCustomerClass: TypeAlias = CustomerClass | Literal["PROPOSED"]
TariffDocumentSectionType: TypeAlias = Literal["SERVICE", "TARIFF", "CLIMATE_ZONE", "UTILITY_CLIMATE_ZONE"]
JsonObject: TypeAlias = dict[str, Any]


class BillingPeriodRepresentation(TypedDict):
    fromDateOffset: int
    "Days to add to Arcadia-style fromDate for the billing period start"
    toDateOffset: int
    "Days to add to Arcadia-style toDate for the billing period end"
    style: BillingPeriodStyle
    "Named billing period representation style"


class LoadServingEntityMinimal(TypedDict):
    """Fields returned in the minimal Load Serving Entity view."""

    lseId: int
    "Unique Arcadia ID (primary key) for each LSE"
    name: str
    "Published name of the company"
    code: str
    "Shortcode (US values match the EIA ID)"
    websiteHome: str
    "URL to the Load Serving Entity home page"


class LoadServingEntityExtendedFields(TypedDict):
    """Fields available when requesting the extended Load Serving Entity view."""

    offeringType: LoadServingOfferingType
    "Classification of services the utility provides"
    ownership: LoadServingOwnership
    "Ownership structure reported by the utility"
    serviceTypes: LoadServingServiceType | None
    "Services offered to all customers"
    totalRevenues: int
    "Annual total revenue in thousands of local currency"
    totalSales: int
    "Annual total sales in megawatt-hours"
    totalCustomers: int
    "Total customer count"
    residentialServiceTypes: LoadServingServiceType | None
    "Services offered to residential customers"
    residentialRevenues: int
    "Annual residential revenue in thousands of local currency"
    residentialSales: int
    "Annual residential sales in megawatt-hours"
    residentialCustomers: int
    "Residential customer count"
    commercialServiceTypes: LoadServingServiceType | None
    "Services offered to commercial customers"
    commercialRevenues: int
    "Annual commercial revenue in thousands of local currency"
    commercialSales: int
    "Annual commercial sales in megawatt-hours"
    commercialCustomers: int
    "Commercial customer count"
    industrialServiceTypes: LoadServingServiceType | None
    "Services offered to industrial customers"
    industrialRevenues: int
    "Annual industrial revenue in thousands of local currency"
    industrialSales: int
    "Annual industrial sales in megawatt-hours"
    industrialCustomers: int
    "Industrial customer count"
    transportationServiceTypes: LoadServingServiceType | None
    "Services offered to transportation customers"
    transportationRevenues: int
    "Annual transportation revenue in thousands of local currency"
    transportationSales: int
    "Annual transportation sales in megawatt-hours"
    transportationCustomers: int
    "Transportation customer count"
    billingPeriodRepresentation: BillingPeriodRepresentation | None
    "Details about how billing periods are represented for this LSE"


class LoadServingEntityExtended(LoadServingEntityMinimal, LoadServingEntityExtendedFields):
    """Convenience type combining minimal and extended Load Serving Entity fields."""


class TariffPropertyChoice(TypedDict):
    value: Required[str]
    "Machine readable option value"
    displayValue: NotRequired[str]
    "Human readable value shown to end users"
    dataValue: NotRequired[str]
    likelihood: NotRequired[float | None]


class TariffMinimalFields(TypedDict):
    tariffId: int
    "Unique Arcadia ID (primary key) for this tariff"
    masterTariffId: int
    "Unique Arcadia ID that persists across all revisions of this tariff"
    tariffCode: str
    "Shortcode that the LSE uses as an alternate name for the tariff"
    tariffName: str
    "Name of the tariff as used by the LSE"
    lseId: int
    "ID of load serving entity this tariff belongs to"
    lseName: str
    "Name of the load-serving entity"
    serviceType: TariffServiceType
    "Type of service for the tariff"


class TariffStandardFields(TypedDict):
    priorTariffId: int
    "Unique Arcadia ID that identifies the prior revision of the tariffId above"
    distributionLseId: int | None
    """
    In states like Texas where the load-serving entity that sells the power is
    different than the load-serving entity that distributes the power, this will
    contain the ID of the distribution LSE. Otherwise, it will be None.
    """
    tariffType: TariffType
    """
    Possible values are:
      DEFAULT - tariff that is automatically given to this service class
      ALTERNATIVE - opt-in alternate tariff for this service class
      OPTIONAL_EXTRA - opt-in extra, such as green power or a smart thermostat program
      RIDER - charge that can apply to multiple tariffs. Often a regulatory-mandated charge
    """
    customerClass: CustomerClass
    """
    Possible values are:
      RESIDENTIAL - homes, apartments etc.
      GENERAL - commercial, industrial, and other business and organization service types
        (often have additional applicability criteria)
      SPECIAL_USE - examples are government, agriculture, street lighting, transportation
      PROPOSED - Utility rates that have been proposed by utilities and approved by utility commissions,
        but are not yet effective (requires product subscription)
    """
    customerCount: int
    "Number of customers that are on this master tariff"
    customerLikelihood: NotRequired[float]
    """
    The likelihood that a customer is on this tariff of all the tariffs in the search results.
    Only populated when getting more than one tariff.
    """
    territoryId: str
    """
    ID of the territory that this tariff applies to.
    This is typically the service area for the LSE in this regulatory region (i.e. a state in the USA)
    """
    effectiveDate: datetime
    "Date on which the tariff was or will be effective"
    endDate: datetime
    "Date on which this tariff is no longer effective. Can be null which means end date is not known or tariff is open-ended"
    effectiveOnRule: TariffEffectiveOnRule
    timeZone: str
    "If populated (usually is), it's the timezone that this tariffs dates and times refer to"
    billingPeriod: str
    "How frequently bills are generated."
    currency: str
    "ISO Currency code that the rates for this tariff refer to (e.g. USD for USA Dollar)"
    chargeTypes: TariffChargeType
    "List of all the different ChargeType rates on this tariff"
    chargePeriod: TariffChargePeriod
    "The most fine-grained period for which charges are calculated."
    hasTimeOfUseRates: bool
    "Indicates whether this tariff contains one or more Time of Use Rate."
    hasTieredRates: bool
    "Indicates whether this tariff contains one or more Tiered Rate."
    hasContractedRates: bool
    """
    Indicates whether this tariff contains one or more Rate that can be contracted
    (sometimes called by-passable or associated with a price to compare).
    """
    hasRateApplicability: bool
    """
    Indicates that one or more rates on this tariff are only applicable to customers with a particular circumstance.
    When true, this will be specified in the TariffProperty collection, and also on the TariffRate or rates in question.
    """


class TariffExtendedFields(TypedDict):
    tariffBookName: str
    "Name of the tariff as it appears in the tariff document"
    lseCode: str
    "Abbreviated name of the load-serving entity"
    customerCountSource: str
    "Where we got the customer count numbers from. Typically FERC (form 1 filings) or Arcadia (our own estimates)."
    closedDate: datetime | None
    """
    Date on which a tariff became closed to new customers,
    but still available for customers who were on it at the time.
    Can be null which means that the tariff is not closed.
    All versions of a particular tariff
    (i.e. those that share a particular masterTariffId)
    will have the same closedDate value.
    """
    minMonthlyConsumption: float | None
    "When applicable, the minimum monthly consumption allowed to be eligible for this tariff."
    maxMonthlyConsumption: float | None
    "When applicable, the maximum monthly consumption allowed to be eligible for this tariff."
    minMonthlyDemand: float | None
    "When applicable, the minimum monthly demand allowed to be eligible for this tariff."
    maxMonthlyDemand: float | None
    "When applicable, the maximum monthly demand allowed to be eligible for this tariff."
    hasTariffApplicability: bool
    "Indicates that this tariff has additional eligibility criteria, as specified in the TariffProperty collection"
    hasNetMetering: bool
    "Indicates whether this tariff contains one or more net metered rates."
    privacy: TariffPrivacy
    "Privacy status of the tariff."


class TariffMinimal(TariffMinimalFields):
    properties: NotRequired[list[TariffPropertyMinimal]]
    "The properties on this tariff."
    rates: NotRequired[list[TariffRateMinimal]]
    "The rates for this tariff."
    documents: NotRequired[list[TariffDocumentMinimal]]
    "The documents for this tariff."


class TariffStandard(TariffStandardFields):
    properties: NotRequired[list[TariffPropertyStandard]]
    "The properties on this tariff."
    rates: NotRequired[list[TariffRateStandard]]
    "The rates for this tariff."
    documents: NotRequired[list[TariffDocumentStandard]]
    "The documents for this tariff."


class TariffExtended(TariffExtendedFields):
    properties: NotRequired[list[TariffPropertyStandard]]
    "The properties on this tariff."
    rates: NotRequired[list[TariffRateExtended]]
    "The rates for this tariff."
    documents: NotRequired[list[TariffDocumentExtended]]
    "The documents for this tariff."


class TariffPropertyMinimal:
    keyName: str
    "Unique name for this property"
    displayName: str
    "The display name of this property"
    keyspace: str
    "Top-level categorization of the property hierarchy"
    family: str
    "Second level categorization of the property hierarchy, below keyspace"
    description: str
    "A longer description of the tariff property"
    dataType: TariffPropertyDataType
    "The data type of this property"
    propertyTypes: TariffPropertyCategory


class TariffPropertyStandardFields:
    period: TariffPropertyPeriod | None
    "If applicable the type of time of use."
    operator: str | None
    "The mathematical operator associated with this property's value, where applicable."
    propertyValue: str | None
    "If applicable the specific value of this property."
    minValue: str | None
    "If applicable the minimum value of this property."
    maxValue: str
    "If applicable the maximum value of this property."
    formulaDetail: str | None
    "If this property is a FORMULA type, the formula details will be in this field."
    choices: list[TariffPropertyChoice]
    "The possible choices for this array"
    isDefault: bool
    "Whether the value of this Property is the default value."


class TariffPropertyStandard(TariffPropertyMinimal, TariffPropertyStandardFields): ...


class TariffRateMinimal:
    tariffRateId: int
    "Unique Arcadia ID (primary key) for each tariff rate"
    tariffId: int
    "Associates the rate with a tariff (foreign key)"
    riderId: int
    "Master Tariff ID of the rider linked to this tariff rate."
    tariffSequenceNumber: int
    "Sequence of this rate in the tariff, for display purposes only (e.g. this is the order on the bill)"
    rateGroupName: str
    "Name of the group this rate belongs to"
    rateName: str | None
    "Name of this rate. Use group name if None"


class TariffRateStandardFields:
    fromDateTime: datetime | None
    "If populated, this indicates the rate's effective date is not the same as that of its tariff"
    toDateTime: datetime | None
    "If populated, this indicates the rates end date is not the same as that of its tariff"
    territory: Territory | None
    "Only populated when this rate applies to a different region than the whole tariff"
    season: Season | None
    "The season this rate applies to. Only used for seasonal rates"
    timeOfUse: TimeOfUse | None
    "The time period this rate applies to. Only used for TOU rates"
    chargeType: TariffChargeType
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
    chargeClass: TariffChargeClass
    chargePeriod: TariffChargePeriod
    "Indicates what period this charge is calculated for. "
    quantityKey: str | None
    "Defines the type of quantity this rate applies to."
    applicabilityKey: str | None
    "Defines the eligibility criteria for this rate"
    variableLimitKey: str | None
    "When populated this defines the variable which determines the upper limit(s) of this rate."
    variableRateKey: str | None
    "The name of the property that defines the variable rate."
    variableFactorKey: str | None
    "The name of the property that defines the variable factor to apply to this rate."


class TariffRateExtendedFields:
    riderTariffId: int | None
    "Tariff ID of the rider attached to this tariff version."
    tariffBookSequenceNumber: int
    "Sequence of this rate in the tariff source document, if it differs from tariffSequenceNumber"
    tariffBookRateGroupName: str
    "Name of the group this rate belongs to in the tariff source document, if it differs from rateGroupName"
    tariffBookRateName: str
    "Name of this rate in the tariff source document, if it differs from rateName"
    transactionType: TariffTransactionType


class Convert:
    def __init__(self, converter) -> None:
        self.converter = converter
