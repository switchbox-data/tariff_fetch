"""Scenario inputs that control one Arcadia-to-URDB conversion run."""

from dataclasses import dataclass, field
from typing import cast, get_args

from tariff_fetch.arcadia.schema.common import RateChargeClass

_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))


@dataclass(frozen=True)
class Scenario:
    """User-selected inputs for converting one Arcadia master tariff."""

    master_tariff_id: int
    year: int
    apply_percentages: bool
    charge_classes: set[RateChargeClass] = field(default_factory=set)
