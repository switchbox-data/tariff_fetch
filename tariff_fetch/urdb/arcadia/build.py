"""Build URDB-style output from Arcadia tariff data for a conversion scenario."""

import logging
from collections.abc import Callable

import typer

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.questionary_typed import confirm
from tariff_fetch.urdb.arcadia.demandschedule import build_demand_schedule
from tariff_fetch.urdb.arcadia.library import Library
from tariff_fetch.urdb.schema import URDBRate

from .energyschedule import build_energy_schedule
from .fixedcharge import build_fixed_charge
from .metadata import build_metadata
from .scenario import Scenario

logger = logging.getLogger(__name__)


def build_urdb(api: ArcadiaSignalAPI, scenario: Scenario, *, interactive_errors: bool = True) -> URDBRate:
    """Build a URDB record by combining energy, fixed-charge, and metadata chunks."""

    library = Library(api, properties=scenario.properties)
    energy_schedule = _build_chunk(
        lambda: build_energy_schedule(scenario, library),
        "energy rate strucutre",
        interactive_errors=interactive_errors,
    )
    demand_schedule = _build_chunk(
        lambda: build_demand_schedule(scenario, library),
        "demand rate structure",
        interactive_errors=interactive_errors,
    )
    fixed_charge = _build_chunk(
        lambda: build_fixed_charge(scenario, library),
        "fixed charges",
        interactive_errors=interactive_errors,
    )
    metadata = _build_chunk(
        lambda: build_metadata(scenario, library),
        "metadata",
        interactive_errors=interactive_errors,
    )

    if hasattr(library, "iter_issues"):
        for issue in library.iter_issues():
            logger.warning(issue)

    return {**energy_schedule, **demand_schedule, **fixed_charge, **metadata}


def _build_chunk(
    builder: Callable[[], URDBRate],
    processing: str,
    *,
    interactive_errors: bool,
) -> URDBRate:
    """Run one converter stage with shared cancellation and recovery behavior."""

    try:
        return builder()
    except typer.Exit:
        raise
    except Exception as e:
        return _confirm_proceed(e, processing, interactive_errors=interactive_errors)


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
