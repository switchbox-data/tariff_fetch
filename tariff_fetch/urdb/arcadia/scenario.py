from dataclasses import dataclass, field
from datetime import date
from typing import Literal, cast, get_args, overload

from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyPrunedDataType
from tariff_fetch.urdb.arcadia.exception import TariffConversionError

_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))


@dataclass(frozen=True)
class Scenario:
    master_tariff_id: int
    year: int
    apply_percentages: bool
    charge_classes: set[RateChargeClass] = field(default_factory=set)
