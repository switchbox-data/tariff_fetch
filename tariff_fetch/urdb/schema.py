from __future__ import annotations

from typing import Annotated, Any, Literal, Required

from pydantic import FailFast, TypeAdapter
from typing_extensions import TypedDict

# --- enums per URDB v7 docs ---
RateSector = Literal["Residential", "Commercial", "Industrial", "Lighting"]
ServiceType = Literal["Bundled", "Energy", "Delivery", "Delivery with Standard Offer"]

VoltageCategory = Literal["Primary", "Secondary", "Transmission"]

PhaseWiring = Literal["Single Phase", "3-Phase", "Single and 3-Phase"]

DemandUnit = Literal["kW", "hp", "kVA", "kW daily", "hp daily", "kVA daily"]
EnergyUnit = Literal["kWh"]

FixedChargeUnit = Literal["$/day", "$/month", "$/year"]
MinChargeUnit = Literal["$/day", "$/month", "$/year"]

DGRule = Literal[
    "Net Metering",
    "Net Billing Instantaneous",
    "Net Billing Hourly",
    "Buy All Sell All",
]

URDBItemType = Literal["Utility_Rates"]  # shown in docs examples :contentReference[oaicite:1]{index=1}


# --- fixed-shape schedules (12 months x 24 hours) ---
Int24_ = tuple[
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
    int,
]
Int24 = tuple[int, ...]
# MonthSchedule = tuple[Int24, Int24, Int24, Int24, Int24, Int24, Int24, Int24, Int24, Int24, Int24, Int24]
MonthSchedule = tuple[Int24, ...]
# Float12 = tuple[float, float, float, float, float, float, float, float, float, float, float, float]
Float12 = tuple[float, ...]
# FlatDemandMonths = tuple[int, int, int, int, int, int, int, int, int, int, int, int]
FlatDemandMonths = tuple[int, ...]


# --- tiers (NO None allowed) ---
class FlatDemandTier(TypedDict, total=False):
    max: float

    rate: Required[float]
    adj: float


class DemandTier(TypedDict, total=False):
    max: float
    rate: Required[float]
    adj: float
    sell: float


class CoincidentTier(TypedDict, total=False):
    max: float
    rate: Required[float]
    adj: float
    sell: float


class EnergyTier(TypedDict, total=False):
    max: float
    unit: EnergyUnit
    rate: Required[float]

    adj: float
    sell: float


# 2-D structures: [period][tier] :contentReference[oaicite:2]{index=2}
FlatDemandStructure = list[list[FlatDemandTier]]
DemandRateStructure = list[list[DemandTier]]
CoincidentRateStructure = list[list[CoincidentTier]]
EnergyRateStructure = list[list[EnergyTier]]

Attrs = list[dict[str, Any]]  # pyright: ignore[reportExplicitAny]


class URDBRate(TypedDict, total=False):
    label: str
    utility: str
    name: str
    uri: str
    type: URDBItemType

    approved: bool
    is_default: bool

    startdate: int
    enddate: int
    supercedes: str

    sector: RateSector
    servicetype: ServiceType

    description: str
    source: str
    sourceparent: str
    basicinformationcomments: str

    peakkwcapacitymin: float
    peakkwcapacitymax: float
    demandunits: DemandUnit
    peakkwcapacityhistory: float

    peakkwhusagemin: float
    peakkwhusagemax: float
    peakkwhusagehistory: float

    voltageminimum: float

    voltagemaximum: float
    voltagecategory: VoltageCategory
    phasewiring: PhaseWiring

    flatdemandunit: DemandUnit

    flatdemandstructure: FlatDemandStructure
    flatdemandmonths: FlatDemandMonths

    demandrateunit: DemandUnit
    demandratestructure: DemandRateStructure
    demandweekdayschedule: MonthSchedule

    demandweekendschedule: MonthSchedule
    demandratchetpercentage: Float12
    demandwindow: float
    demandreactivepowercharge: float

    coincidentrateunit: DemandUnit
    coincidentratestructure: CoincidentRateStructure

    coincidentrateschedule: MonthSchedule

    demandattrs: Attrs
    demandcomments: str
    dgrules: DGRule

    energyratestructure: EnergyRateStructure
    energyweekdayschedule: MonthSchedule
    energyweekendschedule: MonthSchedule
    fueladjustmentsmonthly: Float12
    energyattrs: Attrs
    energycomments: str

    fixedchargefirstmeter: float
    fixedchargeeaaddl: float
    fixedchargeunits: FixedChargeUnit
    mincharge: float
    minchargeunits: MinChargeUnit
    fixedattrs: Attrs

    country: str


URDBRateAdapter: TypeAdapter[URDBRate] = TypeAdapter(URDBRate)
URDBListAdapter: TypeAdapter[list[URDBRate]] = TypeAdapter(Annotated[list[URDBRate], FailFast()])
