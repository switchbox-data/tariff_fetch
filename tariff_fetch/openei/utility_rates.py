import datetime
from collections.abc import Iterator
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
UtilityRateSector: TypeAlias = (
    Literal["Residential"] | Literal["Commercial"] | Literal["Industrial"] | Literal["Lighting"]
)
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

    modified_after: datetime.datetime | int
    "Modified after, datetime or seconds since 1970-01-01T00:00:00, UTC. "
    limit: int
    "Maximum record count 500"
    getpage: str
    """
    Get a specific page name, i.e. getpage=535aeca39bef511109580ee1.
    This is referred to as 'label' in the results.
    """
    ratesforutility: str
    """
    Get rates for a specific utility page name, i.e. ratesforutility=Detroit Edison Co.
    This value can be re-used from the "label" value in the utility_companies results.
    """
    offset: int
    "The offset from which to start retrieving records."
    orderby: str
    "Field to use to sort results."
    direction: Literal["asc"] | Literal["desc"]
    "Direction to order results, ascending or descending."
    effective_on_date: datetime.datetime | int
    "Effective on date, datetime or seconds since 1970-01-01T00:00:00, UTC."
    sector: UtilityRateSector
    "Shows only those rates matching the given sector."
    approved: bool
    "Shows only those rates whose approval status matches the given value."
    is_default: bool
    "Shows only those rates whose 'Is Default' status matches the given value."
    country: str
    "ISO 3 character country code, i.e. country=USA."
    address: str
    "Address for rate, see Google Geocoding API for details. Address or lat/lon may be used, but not both."
    lat: int
    "Latitude for rate. If set, lon must also be set and address must not."
    lon: int
    "Longitude for rate. If set, lat must also be set and address must not."
    radius: int
    "Radius to include surrounding search result, in miles. (min 0, max 200)"
    co_limit: int
    "Maximum number of companies to include in a geographic search (using lat/lon, or address)."
    eia: int
    "EIA Id to look up."
    callback: str
    "callback=<mycallback> - set mycallback as the json callback."
    detail: Literal["full"] | Literal["minimal"]
    """
    detail=full - returns every variable. Since this results in a lot of data that can time-out
    returning to your server, use a limit=500 and set an offset (e.g. 501) if you want more data.
    """


class UtilityRatesResponseItem(TypedDict, total=False):
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
    sector: UtilityRateSector
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


class UtilityRatesResponse(TypedDict):
    items: list[UtilityRatesResponseItem]


def iter_utility_rates(
    api_key: str,
    iter_offset: int = 0,
    format: Literal["json"] | Literal["json_plain"] | Literal["csv"] = "json",
    version: str = "latest",
    **kwargs: Unpack[UtilityRatesParams],
) -> Iterator[UtilityRatesResponseItem]:
    offset = iter_offset
    rows = 1
    while rows:
        response = utility_rates(api_key, format, version, **{**kwargs, "offset": offset})
        items = response["items"]
        rows = len(items)
        offset += rows
        yield from items


def utility_rates(
    api_key: str,
    format: Literal["json"] | Literal["json_plain"] | Literal["csv"] = "json",
    version: str = "latest",
    **kwargs: Unpack[UtilityRatesParams],
) -> UtilityRatesResponse:
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
        UtilityRatesResponse,
        api_request_json(path=UTILITY_RATES_API_PATH, api_key=api_key, format=format, version=version, **kwargs),
    )
