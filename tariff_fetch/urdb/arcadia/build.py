from dataclasses import dataclass

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import URDBRate

from .energyschedule import build_energy_schedule
from .scenario import Scenario


@dataclass(frozen=True)
class URDBChunk:
    fixed_charge: float


def build_urdb(api: ArcadiaSignalAPI, scenario: Scenario) -> URDBRate:
    library = Library(api)
    energy_schedule = build_energy_schedule(scenario, library)
    return {**energy_schedule}
