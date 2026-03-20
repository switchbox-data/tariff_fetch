"""Build URDB-style output from Arcadia tariff data for a conversion scenario."""

import logging

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.questionary_typed import confirm
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import URDBRate

from .energyschedule import build_energy_schedule
from .fixedcharge import build_fixed_charge
from .metadata import build_metadata
from .scenario import Scenario

logger = logging.getLogger(__name__)


def build_urdb(api: ArcadiaSignalAPI, scenario: Scenario, *, interactive_errors: bool = True) -> URDBRate:
    """Build a URDB record by combining energy, fixed-charge, and metadata chunks."""

    library = Library(api)
    try:
        energy_schedule = build_energy_schedule(scenario, library)
    except Exception as e:
        energy_schedule = _confirm_proceed(e, "energy rate strucutre", interactive_errors=interactive_errors)

    try:
        fixed_charge = build_fixed_charge(scenario, library)
    except Exception as e:
        fixed_charge = _confirm_proceed(e, "fixed charges", interactive_errors=interactive_errors)

    try:
        metadata = build_metadata(scenario, library)
    except Exception as e:
        metadata = _confirm_proceed(e, "metadata", interactive_errors=interactive_errors)

    if hasattr(library, "iter_issues"):
        for issue in library.iter_issues():
            logger.warning(issue)

    return {**energy_schedule, **fixed_charge, **metadata}


def _confirm_proceed(e: Exception, processing: str, *, interactive_errors: bool) -> URDBRate:
    """Ask whether to continue after a chunk-level conversion failure."""

    if not interactive_errors:
        raise e from None

    response = confirm(
        f"Error while converting: {processing}: {e}. Continue or print traceback and exit?"
    ).ask_or_exit()
    if response:
        return {}
    raise e from None
