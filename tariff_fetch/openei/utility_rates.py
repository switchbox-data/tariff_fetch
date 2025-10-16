from typing import Any, Literal, TypeAlias, TypedDict, cast

from typing_extensions import Unpack

from .base import api_request_json

UTILITY_RATES_API_PATH = "/utility_rates"
DemandUnit: TypeAlias = (
    Literal["kW"] | Literal["hp"] | Literal["kVA"] | Literal["kW daily"] | Literal["hp daily"] | Literal["kVA daily"]
)
VoltageCategory: TypeAlias = Literal["Primary"] | Literal["Secondary"] | Literal["Transmission"]
PhaseWiring: TypeAlias = Literal["Single Phase"] | Literal["3-Phase"] | Literal["Single and 3-Phase"]
ServiceType: TypeAlias = (
    Literal["Bundled"] | Literal["Energy"] | Literal["Delivery"] | Literal["Delivery with Standard Offer"]
)
FixedChargeUnit: TypeAlias = Literal["$/day"] | Literal["$/month"] | Literal["$/year"]
DistributedGenerationRule: TypeAlias = Literal[
    "Net Metering", "Net Billing Instantaneous", "Net Billing Hourly", "Buy All Sell All"
]
ScheduleMatrix: TypeAlias = list[list[int]]
AttributeList: TypeAlias = list[dict[str, Any]]


class FlatDemandTier(TypedDict, total=False):
    max: float
    rate: float
    adj: float


class DemandRateTier(TypedDict, total=False):
    max: float
    rate: float
    adj: float


class CoincidentRateTier(TypedDict, total=False):
    max: float
    rate: float
    adj: float


class EnergyRateTier(TypedDict, total=False):
    max: float
    unit: str
    rate: float
    adj: float
    sell: float


FlatDemandStructure: TypeAlias = list[list[FlatDemandTier]]
DemandRateStructure: TypeAlias = list[list[DemandRateTier]]
CoincidentRateStructure: TypeAlias = list[list[CoincidentRateTier]]
EnergyRateStructure: TypeAlias = list[list[EnergyRateTier]]


class UtilityRatesParams(TypedDict, total=False):
    """Parameters for utility rates api"""

    limit: int
    " Maximum record count 500. "
    offset: int
    "The offset from which to start retrieving records."
    getpage: str
    """Get a specific page name, i.e. getpage=535aeca39bef511109580ee1.
    This is referred to as 'label' in the results."""
    ratesforutility: str
    """Get rates for a specific utility page name, i.e. ratesforutility=Detroit Edison Co.
    This value can be re-used from the "label" value in the utility_companies results."""
    orderby: str
    "Field to use to sort results. Default: label"
    direction: Literal["asc"] | Literal["desc"]
    "Direction to order results, ascending or descending."
    sector: Literal["Residential"] | Literal["Commercial"] | Literal["Industrial"] | Literal["Lighting"]
    "Shows only those rates matching the given sector."
    approved: bool
    "Shows only those rates whose approval status matches the given value."
    address: str
    "Address for rate, see Google Geocoding API for details. Address or lat/lon may be used, but not both."
    lat: int
    "Latitude for rate. If set, lon must also be set and address must not."
    lon: int
    "Longitude for rate. If set, lat must also be set and address must not."
    eia: int
    "EIA Id to look up."
    detail: Literal["full"] | Literal["minimal"]


class UtilityRatesResponse(TypedDict, total=False):
    label: str
    "Page label"
    utility: str
    "Utility company name"
    name: str
    "Rate name"
    uri: str
    "Full page URI"
    approved: bool
    "Expert has verified"
    is_default: bool
    "Most common rate for given time period, sector, and service type"
    startdate: int
    "Effective date timestamp"
    enddate: int
    "End date timestamp"
    supercedes: str
    "Label of the rate this rate supercedes."
    sector: Literal["Residential"] | Literal["Commercial"] | Literal["Industrial"] | Literal["Lighting"]
    "Sector"
    servicetype: ServiceType
    "Service type"
    description: str
    "Description"
    source: str
    "Source or reference."
    sourceparent: str
    "Source parent URI"
    basicinformationcomments: str
    "Basic comments"
    peakkwcapacitymin: float
    "Demand minimum (kW)"
    peakkwcapacitymax: float
    "Demand maximum (kW)"
    demandunits: DemandUnit
    "Demand applicability units"
    peakkwcapacityhistory: float
    "Demand history (months)"
    peakkwhusagemin: float
    "Energy minimum (kW)"
    peakkwhusagemax: float
    "Energy maximum (kW)"
    peakkwhusagehistory: float
    "Energy history (months)"
    voltageminimum: float
    "Service voltage minimum"
    voltagemaximum: float
    "Service voltage maximum"
    voltagecategory: VoltageCategory
    "Voltage category"
    phasewiring: PhaseWiring
    "Phase wiring"
    flatdemandunit: DemandUnit
    "Seasonal/monthly demand rate units"
    flatdemandstructure: FlatDemandStructure
    "Seasonal/monthly demand charge structure"
    flatdemandmonths: list[int]
    "Seasonal/monthly demand charge schedule"
    demandrateunit: DemandUnit
    "Time-of-use demand rate units"
    demandratestructure: DemandRateStructure
    "Time-of-use demand charge structure"
    demandweekdayschedule: ScheduleMatrix
    "Time-of-use demand weekday schedule"
    demandweekendschedule: ScheduleMatrix
    "Time-of-use demand weekend schedule"
    demandratchetpercentage: list[float]
    "Demand ratchet percentage by month"
    demandwindow: float
    "Demand window (minutes)"
    demandreactivepowercharge: float
    "Demand reactive power charge ($/kVAR)"
    coincidentrateunit: DemandUnit
    "Coincident demand rate units"
    coincidentratestructure: CoincidentRateStructure
    "Coincident demand charge structure"
    coincidentrateschedule: ScheduleMatrix
    "Coincident demand schedule"
    demandattrs: AttributeList
    "Demand attribute key/value pairs"
    demandcomments: str
    "Demand comments"
    dgrules: DistributedGenerationRule
    "Distributed generation compensation rules"
    energyratestructure: EnergyRateStructure
    "Tiered energy usage charge structure"
    energyweekdayschedule: ScheduleMatrix
    "Tiered energy weekday schedule"
    energyweekendschedule: ScheduleMatrix
    "Tiered energy weekend schedule"
    fueladjustmentsmonthly: list[float]
    "Fuel adjustments by month ($/kWh)"
    energyattrs: AttributeList
    "Energy attribute key/value pairs"
    energycomments: str
    "Energy comments"
    fixedchargefirstmeter: float
    "Fixed charge for first meter"
    fixedchargeeaaddl: float
    "Fixed charge for each additional meter"
    fixedchargeunits: FixedChargeUnit
    "Units for fixed charge values"
    mincharge: float
    "Minimum charge"
    minchargeunits: FixedChargeUnit
    "Units for minimum charge"
    fixedattrs: AttributeList
    "Fixed charge attribute key/value pairs"


def utility_rates(
    api_key: str,
    format: Literal["json"] | Literal["json_plain"] | Literal["csv"] = "json",
    version: str = "latest",
    **kwargs: Unpack[UtilityRatesParams],
) -> list:
    """Access utility rate structure information from the U.S. Utility Rate Database

    Args:
        api_key: api key (register at https://openei.org/services/api/signup/)

        format: The format parameter will be disregarded if the debug parameter is set

        version: API version to use

          OpenEI retired the version 1 API on January 2nd, 2014.
          Version 2 was released on May 4th, 2013, and version 3 was released on June 16th, 2014,
          at which point version 2 database updates ceased, with all updates now appearing only
          in version 3 or greater.
    """
    return cast(
        list, api_request_json(path=UTILITY_RATES_API_PATH, api_key=api_key, format=format, version=version, **kwargs)
    )
