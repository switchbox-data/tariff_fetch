from dataclasses import dataclass
from typing import cast

import questionary

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import URDBRate

from .energyschedule import build_energy_schedule
from .fixedcharge import build_fixed_charge
from .scenario import Scenario


@dataclass(frozen=True)
class URDBChunk:
    fixed_charge: float


def build_urdb(api: ArcadiaSignalAPI, scenario: Scenario) -> URDBRate:
    library = Library(api)
    try:
        energy_schedule = build_energy_schedule(scenario, library)
    except Exception as e:
        energy_schedule = _confirm_proceed(e, "energy rate strucutre")

    try:
        fixed_charge = build_fixed_charge(scenario, library)
    except Exception as e:
        fixed_charge = _confirm_proceed(e, "fixed charges")
    return {**energy_schedule, **fixed_charge}


def _confirm_proceed(e: Exception, processing: str) -> URDBRate:
    response = cast(
        bool | None,
        questionary.confirm(f"Error while converting: {processing}: {e}. Continue or print traceback and exit?").ask(),
    )
    if response is None:
        exit()
    if response:
        return {}
    raise e from None
