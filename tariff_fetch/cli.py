import json
import logging
import os
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, BinaryIO, Literal, NamedTuple, TypeVar, cast, get_args
from urllib.request import urlopen

import polars as pl
import typer
from dotenv import load_dotenv
from pathvalidate import sanitize_filename
from platformdirs import user_cache_dir
from pydantic import TypeAdapter
from rich.logging import RichHandler
from rich.table import Table

from tariff_fetch._cli.arcadia_urdb import process_genability as process_genability_urdb
from tariff_fetch._cli.genability import process_genability
from tariff_fetch._cli.openei import process_openei
from tariff_fetch._cli.rateacuity import (
    fetch_rateacuity_gas_tariffs,
    fetch_rateacuity_tariffs,
    process_rateacuity,
    process_rateacuity_gas,
)
from tariff_fetch._cli.rateacuity_gas_urdb import fetch_rateacuity_gas_urdb_rates, process_rateacuity_gas_urdb
from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema import tariff
from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.openei.utility_rates import UtilityRateSector, UtilityRatesResponseItem, iter_utility_rates
from tariff_fetch.rateacuity.base import AuthorizationError
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.scenario import Scenario, ScenarioPropertyValue

from . import questionary_typed as q
from ._cli import console
from ._cli.types import Provider, StateCode, Utility

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=False,
)

urdb_app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(urdb_app, name="urdb", help="Convert Arcadia tariffs to URDB JSON.")

gas_app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(gas_app, name="gas", help="Fetch and convert RateAcuity gas tariffs.")

gas_urdb_app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
)
gas_app.add_typer(gas_urdb_app, name="urdb", help="Convert RateAcuity gas tariffs to URDB format.")

ni_app = typer.Typer(
    invoke_without_command=False,
    no_args_is_help=True,
)
app.add_typer(ni_app, name="ni", help="Fetch provider data directly by identifier.")

rateacuity_ni_app = typer.Typer(
    invoke_without_command=False,
    no_args_is_help=True,
)
ni_app.add_typer(
    rateacuity_ni_app,
    name="rateacuity",
    help="Fetch RateAcuity tariffs in non-interactive modes.",
)

cache_app = typer.Typer(
    invoke_without_command=False,
    no_args_is_help=True,
)
app.add_typer(cache_app, name="cache", help="Manage local CLI caches.")

ENTITY_TYPES_SORTORDER = ["Investor Owned", "Cooperative", "Municipal"]
CORE_EIA861_YEARLY_SALES_HTTPS = (
    "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_eia861__yearly_sales.parquet"
)
UTILITY_CACHE_TTL_SECONDS = 60 * 60
UTILITY_CACHE_DIR = Path(user_cache_dir("tariff_fetch"))
UTILITY_CACHE_PATH = UTILITY_CACHE_DIR / "core_eia861__yearly_sales.parquet"
LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
ALL_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))
CHARGE_CLASS_SHORTCUTS: dict[str, RateChargeClass] = {
    "S": "SUPPLY",
    "T": "TRANSMISSION",
    "D": "DISTRIBUTION",
    "t": "TAX",
    "C": "CONTRACTED",
    "U": "USER_ADJUSTED",
    "A": "AFTER_TAX",
    "O": "OTHER",
    "N": "NON_BYPASSABLE",
    "n": "NET_EXCESS",
}
_T = TypeVar("_T")


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@app.callback()
def main_default(
    ctx: typer.Context,
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    provider: Annotated[Provider | None, typer.Option("--provider", "-p", case_sensitive=False)] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    effective_date: Annotated[
        str | None, typer.Option("--effective-date", help="Effective date for provider queries in YYYY-MM-DD format")
    ] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    if ctx.invoked_subcommand is not None:
        return
    _configure_interaction(no_input)
    _run_raw(
        state,
        provider,
        output_folder,
        _parse_effective_date(effective_date),
        _log_level_to_int(log_level),
        log_dir,
        log_file,
    )


@app.command("raw", help="Fetch raw tariff data from the selected provider.")
def main_raw(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    provider: Annotated[Provider | None, typer.Option("--provider", "-p", case_sensitive=False)] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    effective_date: Annotated[
        str | None, typer.Option("--effective-date", help="Effective date for provider queries in YYYY-MM-DD format")
    ] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    _configure_interaction(no_input)
    _run_raw(
        state,
        provider,
        output_folder,
        _parse_effective_date(effective_date),
        _log_level_to_int(log_level),
        log_dir,
        log_file,
    )


@urdb_app.callback()
def main_urdb(
    ctx: typer.Context,
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    year: Annotated[int | None, typer.Option("--year", "-y")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Raise conversion errors immediately instead of prompting to continue"),
    ] = False,
    properties: Annotated[
        list[str] | None,
        typer.Option("--property", help="Tariff property override in key=value form; repeat for multiple values"),
    ] = None,
):
    if ctx.invoked_subcommand is not None:
        return
    _configure_interaction(no_input)
    state_ = state or prompt_state().value
    output_folder_ = Path(output_folder)
    _ = _configure_command_logging(
        "tariff_fetch_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    utility = prompt_utility(state_)
    year = prompt_year() if year is None else year

    console.print("Processing [blue]Genability[/]")
    _run_cli_command(
        lambda: process_genability_urdb(
            utility=utility,
            output_folder=output_folder_,
            year=year,
            interactive_errors=not fail_fast,
            properties=_parse_property_assignments(properties),
        )
    )


@urdb_app.command("ni", help="Convert a specific Arcadia master tariff directly to URDB JSON.")
def urdb_direct(
    master_tariff_id: Annotated[int, typer.Argument(help="Arcadia master tariff id to convert")],
    year: Annotated[int, typer.Argument(help="Calendar year to convert")],
    charge_classes: Annotated[
        list[str] | None,
        typer.Option("--charge-class", help="Arcadia charge class to include; repeat to include multiple"),
    ] = None,
    charge_class_shortcuts: Annotated[
        list[str] | None,
        typer.Option(
            "--cc",
            help=(
                "Compact Arcadia charge-class selector. "
                "Codes: S=SUPPLY T=TRANSMISSION D=DISTRIBUTION t=TAX "
                "C=CONTRACTED U=USER_ADJUSTED A=AFTER_TAX O=OTHER "
                "N=NON_BYPASSABLE n=NET_EXCESS"
            ),
        ),
    ] = None,
    apply_percentages: Annotated[
        bool,
        typer.Option("--apply-percentages/--no-apply-percentages", help="Apply supported percentage rates"),
    ] = True,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Raise conversion errors immediately instead of prompting to continue"),
    ] = False,
    properties: Annotated[
        list[str] | None,
        typer.Option("--property", help="Tariff property override in key=value form; repeat for multiple values"),
    ] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the converted URDB JSON")] = None,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _configure_interaction(no_input)
    _ = load_dotenv()
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    if output.is_dir():
        output = output / f"arcadia_urdb_{master_tariff_id}_{year}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)
    _ = _configure_command_logging(
        "tariff_fetch_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output.parent / "logs"),
        log_file=log_file,
    )
    scenario_charge_classes = _parse_charge_classes(charge_classes, charge_class_shortcuts)
    scenario = Scenario(
        master_tariff_id=master_tariff_id,
        year=year,
        apply_percentages=apply_percentages,
        charge_classes=scenario_charge_classes,
        properties=_parse_property_assignments(properties),
    )
    api = ArcadiaSignalAPI()
    result = _run_cli_command(lambda: build_urdb(api, scenario, interactive_errors=not fail_fast))
    _ = output.write_text(json.dumps(result, indent=2))


@gas_app.callback()
def main_gas(
    ctx: typer.Context,
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    if ctx.invoked_subcommand is not None:
        return

    _configure_interaction(no_input)
    state_ = (state or prompt_state()).value
    output_folder_ = Path(output_folder)
    _ = _configure_command_logging(
        "tariff_fetch_gas",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    _run_rateacuity_command(lambda: process_rateacuity_gas(output_folder_, state_))


@gas_urdb_app.callback()
def main_gas_urdb(
    ctx: typer.Context,
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    year: Annotated[int | None, typer.Option("--year", "-y")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    if ctx.invoked_subcommand is not None:
        return
    _configure_interaction(no_input)
    state_ = (state or prompt_state()).value
    output_folder_ = Path(output_folder)
    year_ = prompt_year() if year is None else year
    _ = _configure_command_logging(
        "tariff_fetch_gas_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    _run_rateacuity_command(lambda: process_rateacuity_gas_urdb(output_folder_, state_, year_))


@gas_urdb_app.command("ni", help="Convert gas RateAcuity tariffs to URDB using fuzzy-matched utility and tariff names.")
def main_gas_urdb_ni(
    state: Annotated[StateCode, typer.Argument(help="Two-letter state abbreviation")],
    utility: Annotated[str, typer.Argument(help="Utility name query to fuzzy-match against RateAcuity choices")],
    year: Annotated[int, typer.Option("--year", "-y", help="Calendar year to convert")],
    tariffs: Annotated[
        list[str] | None,
        typer.Option("--tariff", help="Tariff name query to fuzzy-match; repeat to include multiple tariffs"),
    ] = None,
    label: Annotated[
        str | None,
        typer.Option("--label", help="URDB label override; defaults to an acronym derived from the utility name"),
    ] = None,
    sector: Annotated[
        Literal["Residential", "Commercial", "Industrial", "Lighting"],
        typer.Option("--sector", help="URDB sector"),
    ] = "Residential",
    servicetype: Annotated[
        Literal["Bundled", "Energy", "Delivery", "Delivery with Standard Offer"],
        typer.Option("--servicetype", help="URDB service type"),
    ] = "Bundled",
    apply_percentages: Annotated[
        bool,
        typer.Option("--apply-percentages/--no-apply-percentages", help="Apply supported percentage rows"),
    ] = False,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the converted URDB JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _run_rateacuity_gas_urdb_ni(
        state=state.value,
        utility_query=utility,
        year=year,
        tariffs=tariffs,
        label=label,
        sector=sector,
        servicetype=servicetype,
        apply_percentages=apply_percentages,
        output=output,
        log_level=log_level,
        no_input=no_input,
        log_dir=log_dir,
        log_file=log_file,
        force=force,
    )


@gas_app.command("ni", help="Fetch gas RateAcuity tariffs by fuzzy-matched state, utility, and tariff names.")
def main_gas_fuzzy(
    state: Annotated[StateCode, typer.Argument(help="Two-letter state abbreviation")],
    utility: Annotated[str, typer.Argument(help="Utility name query to fuzzy-match against RateAcuity choices")],
    tariffs: Annotated[
        list[str] | None,
        typer.Option("--tariff", help="Tariff name query to fuzzy-match; repeat to include multiple tariffs"),
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the fetched tariff JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _run_rateacuity_gas_ni(
        state=state.value,
        utility_query=utility,
        tariffs=tariffs,
        output=output,
        log_level=log_level,
        no_input=no_input,
        log_dir=log_dir,
        log_file=log_file,
        force=force,
    )


@ni_app.command("arcadia", help="Fetch a specific Arcadia master tariff as raw JSON.")
def ni_arcadia(
    master_tariff_id: Annotated[int, typer.Argument(help="Arcadia master tariff id to fetch")],
    effective_date: Annotated[
        str | None,
        typer.Argument(help="Effective date in YYYY-MM-DD format; defaults to today if omitted"),
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the fetched tariff JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _configure_interaction(no_input)
    _ = load_dotenv()
    effective_on = _parse_effective_date(effective_date) or date.today()
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    if output.is_dir():
        output = output / f"arcadia_{master_tariff_id}_{effective_on.isoformat()}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)

    _ = _configure_command_logging(
        "tariff_fetch_ni_arcadia",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output.parent / "logs"),
        log_file=log_file,
    )
    results = _run_cli_command(
        lambda: _fetch_arcadia_tariffs(
            master_tariff_id=master_tariff_id,
            effective_on=effective_on,
            populate_rates=True,
        )
    )
    _ = output.write_bytes(TypeAdapter(list[tariff.TariffExtended]).dump_json(results, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {output}")


@ni_app.command("openei", help="Fetch OpenEI tariffs for a specific utility EIA id as raw JSON.")
def ni_openei(
    eia_id: Annotated[int, typer.Argument(help="Utility EIA id to fetch tariffs for")],
    sector: Annotated[
        Literal["Residential", "Commercial", "Industrial", "Lighting"],
        typer.Argument(help="OpenEI sector to fetch"),
    ],
    effective_date: Annotated[
        str | None,
        typer.Argument(help="Effective date in YYYY-MM-DD format; defaults to today if omitted"),
    ] = None,
    detail: Annotated[
        Literal["full", "minimal"], typer.Option("--detail", help="OpenEI response detail level")
    ] = "full",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the fetched tariff JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _configure_interaction(no_input)
    _ = load_dotenv()
    effective_on = _parse_effective_date(effective_date) or date.today()
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    if output.is_dir():
        output = output / f"openei_{eia_id}_{sector}_{detail}_{effective_on.isoformat()}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)

    _ = _configure_command_logging(
        "tariff_fetch_ni_openei",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output.parent / "logs"),
        log_file=log_file,
    )
    results = _run_cli_command(
        lambda: _fetch_openei_tariffs(eia_id=eia_id, sector=sector, detail=detail, effective_on=effective_on)
    )
    _ = output.write_text(json.dumps({"items": results}, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] items to {output}")


@rateacuity_ni_app.command("fuzzy", help="Fetch RateAcuity tariffs by fuzzy-matched state, utility, and tariff names.")
def ni_rateacuity_fuzzy(
    state: Annotated[StateCode, typer.Argument(help="Two-letter state abbreviation")],
    utility: Annotated[str, typer.Argument(help="Utility name query to fuzzy-match against RateAcuity choices")],
    tariffs: Annotated[
        list[str] | None,
        typer.Option("--tariff", help="Tariff name query to fuzzy-match; repeat to include multiple tariffs"),
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the fetched tariff JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _run_rateacuity_ni(
        state=state.value,
        utility_query=utility,
        tariffs=tariffs,
        output=output,
        log_level=log_level,
        no_input=no_input,
        log_dir=log_dir,
        log_file=log_file,
        force=force,
    )


@rateacuity_ni_app.command("eia-id", help="Fetch RateAcuity tariffs by utility EIA id via the cached parquet.")
def ni_rateacuity_eia_id(
    eia_id: Annotated[int, typer.Argument(help="Utility EIA id to resolve via the cached utilities parquet")],
    tariffs: Annotated[
        list[str] | None,
        typer.Option("--tariff", help="Tariff name query to fuzzy-match; repeat to include multiple tariffs"),
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the fetched tariff JSON")] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    utility_record = _get_utility_by_eia_id(eia_id)
    _run_rateacuity_ni(
        state=utility_record.state.lower(),
        utility_query=utility_record.name,
        tariffs=tariffs,
        output=output,
        log_level=log_level,
        no_input=no_input,
        log_dir=log_dir,
        log_file=log_file,
        force=force,
    )


@app.command("show-properties", help="Show Arcadia tariff properties for a master tariff.")
def show_properties(
    master_tariff_id: Annotated[int, typer.Argument(help="Arcadia master tariff id to inspect")],
    effective_date: Annotated[
        str | None,
        typer.Argument(help="Effective date in YYYY-MM-DD format; defaults to today if omitted"),
    ] = None,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    no_input: Annotated[
        bool, typer.Option("--no-input", help="Fail instead of prompting for interactive input")
    ] = False,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    _configure_interaction(no_input)
    _ = load_dotenv()
    effective_on = _parse_effective_date(effective_date) or date.today()
    _ = _configure_command_logging(
        "tariff_fetch_show_properties_arcadia",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (Path("./outputs") / "logs"),
        log_file=log_file,
    )
    tariffs = _run_cli_command(
        lambda: _fetch_arcadia_tariffs(
            master_tariff_id=master_tariff_id,
            effective_on=effective_on,
            populate_rates=True,
        )
    )
    _print_arcadia_properties(tariffs)


@cache_app.command("clear", help="Delete the cached EIA utility parquet file.")
def clear_cache():
    if not UTILITY_CACHE_PATH.exists():
        console.print(f"No cached utilities parquet found at [blue]{UTILITY_CACHE_PATH}[/]")
        return

    UTILITY_CACHE_PATH.unlink()
    console.print(f"Cleared cached utilities parquet at [blue]{UTILITY_CACHE_PATH}[/]")


@cache_app.command("location", help="Show the cached EIA utility parquet file path.")
def cache_location():
    console.print(f"Utility parquet cache path: [blue]{UTILITY_CACHE_PATH}[/]")


def main_cli():
    app()


def _run_raw(
    state: StateCode | None,
    provider: Provider | None,
    output_folder: str,
    effective_date: date | None,
    log_level: int,
    log_dir: Path | None,
    log_file: Path | None,
):
    state_ = state or prompt_state().value
    provider = provider or prompt_provider()
    output_folder_ = Path(output_folder)
    _ = _configure_command_logging(
        "tariff_fetch",
        log_level=log_level,
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    utility = prompt_utility(state_)

    match provider:
        case Provider.GENABILITY:
            console.print("Processing [blue]Genability[/]")
            _run_cli_command(
                lambda: process_genability(utility=utility, output_folder=output_folder_, effective_on=effective_date)
            )
        case Provider.OPENEI:
            console.print("Processing [blue]OpenEI[/]")
            _run_cli_command(lambda: process_openei(utility, output_folder_, effective_on=effective_date))
        case Provider.RATEACUITY:
            _run_rateacuity_command(lambda: process_rateacuity(output_folder_, state_, utility))


def _configure_logging(
    suffix: str,
    *,
    log_level: int,
    log_dir: Path | None = None,
    log_file: Path | None = None,
) -> Path:
    if log_dir is not None and log_file is not None:
        raise typer.BadParameter("Use either --log-dir or --log-file, not both.")

    if log_file is None:
        log_dir = log_dir or Path("./outputs/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = log_dir / f"{suffix}_{timestamp}.log"
    else:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        path = log_file

    rich_handler = RichHandler(rich_tracebacks=True)
    rich_handler.setLevel(log_level)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(level=log_level, handlers=[rich_handler, file_handler], force=True)
    _configure_noisy_loggers(log_level)
    return path


def _configure_command_logging(
    suffix: str,
    *,
    log_level: int,
    log_dir: Path | None = None,
    log_file: Path | None = None,
) -> Path:
    log_path = _configure_logging(suffix, log_level=log_level, log_dir=log_dir, log_file=log_file)
    console.print(f"Logging to [blue]{log_path}[/]")
    return log_path


def _configure_interaction(no_input: bool) -> None:
    q.set_no_input(no_input)


def _run_cli_command(command: Callable[[], _T]) -> _T:
    try:
        return command()
    except typer.Exit as e:
        _handle_expected_exit(e)
        raise AssertionError("unreachable") from None
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise typer.Exit(1) from e


def _run_rateacuity_command(command: Callable[[], _T]) -> _T:
    try:
        return command()
    except typer.Exit as e:
        _handle_expected_exit(e)
        raise AssertionError("unreachable") from None
    except AuthorizationError:
        _print_authorization_failed()
        raise typer.Exit(1) from None
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise typer.Exit(1) from e


def _print_authorization_failed() -> None:
    console.print("Authorization failed")
    console.print(
        "Check if credentials provided via [b]RATEACUITY_USERNAME[/] and [b]RATEACUITY_PASSWORD[/] environment variables are correct"
    )


def _parse_effective_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("Effective date must be in YYYY-MM-DD format.") from exc


def _log_level_to_int(value: LogLevel) -> int:
    level = getattr(logging, value.value, None)
    if not isinstance(level, int):
        raise typer.BadParameter(f"Unsupported log level: {value.value}")
    return level


def _configure_noisy_loggers(log_level: int) -> None:
    # Browser automation pulls in urllib3/http chatter and asyncio selector noise.
    noisy_logger_names = (
        "selenium",
        "urllib3",
        "urllib3.connectionpool",
        "asyncio",
    )
    noisy_level = max(log_level, logging.INFO)
    for logger_name in noisy_logger_names:
        logging.getLogger(logger_name).setLevel(noisy_level)


def _handle_expected_exit(exc: typer.Exit) -> None:
    if exc.exit_code not in (None, 0):
        console.print("[yellow]Cancelled by user[/]")
    raise exc


def prompt_provider() -> Provider:
    return q.select(
        message="Select provider",
        choices=[q.Choice(title=provider.value, value=provider) for provider in Provider],
    ).ask_or_exit()


class _UtilityLookup(NamedTuple):
    eia_id: int
    name: str
    state: str


def prompt_utility(state: str) -> Utility:
    with console.status("Fetching utilities..."):
        yearly_sales_df = (
            pl.read_parquet(_get_cached_utility_sales_parquet())  # pyright: ignore[reportUnknownMemberType]
            .filter(pl.col("state") == state.upper())
            .filter(pl.col("report_date") == pl.col("report_date").max().over("utility_id_eia"))  # pyright: ignore[reportUnknownMemberType]
            .filter(pl.col("entity_type").is_in(ENTITY_TYPES_SORTORDER))
            .group_by("utility_id_eia")
            .agg(
                pl.col("utility_name_eia").last().alias("utility_name"),
                pl.col("business_model").last().alias("business_model"),
                pl.col("sales_mwh").filter(pl.col("customer_class") == "residential").sum().alias("sales_mwh"),
                pl.col("sales_revenue").sum().alias("sales_revenue"),
                pl.col("customers").filter(pl.col("customer_class") == "residential").sum().alias("customers"),
                pl.col("entity_type").last().alias("entity_type"),
            )
            .sort(["entity_type", "customers", "utility_name"], descending=(False, True, False))
        )

        rows = list(yearly_sales_df.iter_rows(named=True))
        rows.sort(
            key=lambda _: (
                ENTITY_TYPES_SORTORDER.index(_["entity_type"])  # pyright: ignore[reportAny]
                if _["entity_type"] in ENTITY_TYPES_SORTORDER
                else abs(hash(_["entity_type"])) + 4,  # pyright: ignore[reportAny]
                -_["customers"],
                _["utility_name"],
            )
        )

    def fmt_number(value: float | int | None) -> str:
        if value is None:
            return "-"
        return f"{value:,.0f}"

    utility_name_header = "Utility Name"
    eia_id_header = "EIA ID"
    entity_type_header = "Entity Type"
    sales_header = "Sales (MWh)"
    revenue_header = "Revenue ($)"
    customers_header = "Customers"

    largest_utility_name = max(len(utility_name_header), *(len(row["utility_name"]) for row in rows))  # pyright: ignore[reportAny]
    largest_eia_id = max(len(eia_id_header), *(len(str(row["utility_id_eia"])) for row in rows))  # pyright: ignore[reportAny]
    largest_entity_type = max(len(entity_type_header), *(len(row["entity_type"][:18]) for row in rows))  # pyright: ignore[reportAny]
    largest_sales_col = max(len(sales_header), *(len(fmt_number(row["sales_mwh"])) for row in rows))  # pyright: ignore[reportAny]
    largest_revenue_col = max(len(revenue_header), *(len(fmt_number(row["sales_revenue"])) for row in rows))  # pyright: ignore[reportAny]
    largest_customers_col = max(len(customers_header), *(len(fmt_number(row["customers"])) for row in rows))  # pyright: ignore[reportAny]

    header_str_utility_name = utility_name_header.ljust(largest_utility_name)
    header_str_eia_id = eia_id_header.ljust(largest_eia_id)
    header_str_entity_type = entity_type_header.ljust(largest_entity_type)
    header_str_sales = sales_header.ljust(largest_sales_col)
    header_str_revenue = revenue_header.ljust(largest_revenue_col)
    header_str_customers = customers_header.ljust(largest_customers_col)
    header_str = (
        f"{header_str_utility_name} | {header_str_eia_id} | {header_str_entity_type} | "
        f"{header_str_sales} | {header_str_revenue} | {header_str_customers}"
    )
    separator = q.Separator(line="-" * len(header_str))

    header = q.Choice[Utility | None](
        title=header_str,
        value=None,
    )

    def build_choice(row: dict[str, str | int | float | None]) -> q.Choice[Utility | None]:
        name_col = cast(str, row["utility_name"]).ljust(largest_utility_name)
        eia_id_col = str(cast(int, row["utility_id_eia"])).ljust(largest_eia_id)
        entity_type = (cast(str, row["entity_type"]) or "-")[:18].ljust(largest_entity_type)
        sales_col = fmt_number(cast(float, row["sales_mwh"])).ljust(largest_sales_col)
        revenue_col = fmt_number(cast(float, row["sales_revenue"])).ljust(largest_revenue_col)
        customers_col = fmt_number(cast(float, row["customers"])).ljust(largest_customers_col)
        title = f"{name_col} | {eia_id_col} | {entity_type} | {sales_col} | {revenue_col} | {customers_col}"
        return q.Choice(
            title=title,
            value=Utility(eia_id=cast(int, row["utility_id_eia"]), name=cast(str, row["utility_name"])),
        )

    result: Utility | None = None
    while result is None:
        result = q.select(
            message="Select a utility",
            choices=[header, separator, *[build_choice(row) for row in rows]],
            use_search_filter=True,
            use_jk_keys=False,
            use_shortcuts=False,
        ).ask_or_exit()
    return result


def _get_utility_by_eia_id(eia_id: int) -> _UtilityLookup:
    with console.status("Resolving utility from cached parquet..."):
        rows = (
            pl.read_parquet(_get_cached_utility_sales_parquet())  # pyright: ignore[reportUnknownMemberType]
            .filter(pl.col("utility_id_eia") == eia_id)
            .filter(pl.col("report_date") == pl.col("report_date").max().over("utility_id_eia"))  # pyright: ignore[reportUnknownMemberType]
            .select("utility_id_eia", "utility_name_eia", "state")
            .unique()
            .iter_rows(named=True)
        )
        row = next(rows, None)

    if row is None:
        raise typer.BadParameter(
            f"No utility with EIA ID {eia_id} was found in the cached parquet.", param_hint="--eia-id"
        )

    return _UtilityLookup(
        eia_id=cast(int, row["utility_id_eia"]),
        name=cast(str, row["utility_name_eia"]),
        state=cast(str, row["state"]),
    )


def prompt_year() -> int:
    result = q.text("Enter year", default=str(date.today().year - 1), validate=_is_valid_year).ask_or_exit()
    return int(result)


def prompt_state() -> StateCode:
    return q.select(
        message="Select state",
        choices=[q.Choice(title=state.value.upper(), value=state) for state in StateCode],
        use_search_filter=True,
        use_jk_keys=False,
        use_shortcuts=False,
    ).ask_or_exit()


def _parse_charge_classes(
    charge_classes: list[str] | None, charge_class_shortcuts: list[str] | None = None
) -> set[RateChargeClass]:
    if charge_classes is None and charge_class_shortcuts is None:
        return set(ALL_CHARGE_CLASSES)

    normalized = [charge_class.strip().upper() for charge_class in (charge_classes or [])]
    invalid = sorted(set(normalized) - set(ALL_CHARGE_CLASSES))
    shortcut_invalid = sorted(
        {code for shortcut in charge_class_shortcuts or [] for code in shortcut if code not in CHARGE_CLASS_SHORTCUTS}
    )
    if shortcut_invalid:
        allowed = "".join(CHARGE_CLASS_SHORTCUTS)
        console.print(f"[red]Invalid --cc codes:[/] {', '.join(shortcut_invalid)}")
        console.print(f"Allowed values: {allowed}")
        raise typer.Exit(code=1)
    normalized.extend(CHARGE_CLASS_SHORTCUTS[code] for shortcut in charge_class_shortcuts or [] for code in shortcut)
    if invalid:
        allowed = ", ".join(ALL_CHARGE_CLASSES)
        console.print(f"[red]Invalid charge classes:[/] {', '.join(invalid)}")
        console.print(f"Allowed values: {allowed}")
        raise typer.Exit(code=1)
    return {cast(RateChargeClass, charge_class) for charge_class in normalized}


def _run_rateacuity_ni(
    *,
    state: str,
    utility_query: str,
    tariffs: list[str] | None,
    output: Path | None,
    log_level: LogLevel,
    no_input: bool,
    log_dir: Path | None,
    log_file: Path | None,
    force: bool,
) -> None:
    _configure_interaction(no_input)
    if not tariffs:
        raise typer.BadParameter("Pass at least one --tariff value.", param_hint="--tariff")
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    elif output.exists() and output.is_file() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)

    _ = _configure_command_logging(
        "tariff_fetch_ni_rateacuity",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or ((output if output.is_dir() else output.parent) / "logs"),
        log_file=log_file,
    )
    selected_utility, results = _run_rateacuity_command(
        lambda: fetch_rateacuity_tariffs(state=state, utility_query=utility_query, tariff_queries=tariffs)
    )
    if output.is_dir():
        output = output / f"{sanitize_filename(f'rateacuity_{selected_utility}')}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps(results, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {output}")


def _run_rateacuity_gas_ni(
    *,
    state: str,
    utility_query: str,
    tariffs: list[str] | None,
    output: Path | None,
    log_level: LogLevel,
    no_input: bool,
    log_dir: Path | None,
    log_file: Path | None,
    force: bool,
) -> None:
    _configure_interaction(no_input)
    if not tariffs:
        raise typer.BadParameter("Pass at least one --tariff value.", param_hint="--tariff")
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    elif output.exists() and output.is_file() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)

    _ = _configure_command_logging(
        "tariff_fetch_gas_fuzzy",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or ((output if output.is_dir() else output.parent) / "logs"),
        log_file=log_file,
    )
    selected_utility, results = _run_rateacuity_command(
        lambda: fetch_rateacuity_gas_tariffs(state=state, utility_query=utility_query, tariff_queries=tariffs)
    )
    if output.is_dir():
        output = output / f"{sanitize_filename(f'gas_rateacuity_{selected_utility}')}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps(results, indent=2))
    console.print(f"Wrote [blue]{len(results)}[/] records to {output}")


def _run_rateacuity_gas_urdb_ni(
    *,
    state: str,
    utility_query: str,
    year: int,
    tariffs: list[str] | None,
    label: str | None,
    sector: Literal["Residential", "Commercial", "Industrial", "Lighting"],
    servicetype: Literal["Bundled", "Energy", "Delivery", "Delivery with Standard Offer"],
    apply_percentages: bool,
    output: Path | None,
    log_level: LogLevel,
    no_input: bool,
    log_dir: Path | None,
    log_file: Path | None,
    force: bool,
) -> None:
    _configure_interaction(no_input)
    if not tariffs:
        raise typer.BadParameter("Pass at least one --tariff value.", param_hint="--tariff")
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    elif output.exists() and output.is_file() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)

    _ = _configure_command_logging(
        "tariff_fetch_gas_urdb_ni",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or ((output if output.is_dir() else output.parent) / "logs"),
        log_file=log_file,
    )
    selected_utility, result = _run_rateacuity_command(
        lambda: fetch_rateacuity_gas_urdb_rates(
            state=state,
            utility_query=utility_query,
            tariff_queries=tariffs,
            year=year,
            apply_percentages=apply_percentages,
            label=label,
            sector=sector,
            servicetype=servicetype,
        )
    )
    if output.is_dir():
        output = output / f"{sanitize_filename(f'rateacuity_{selected_utility}.urdb.{year}.')}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps({"items": result}, indent=2))
    console.print(f"Wrote [blue]{len(result)}[/] items to {output}")


def _parse_property_assignments(values: list[str] | None) -> dict[str, ScenarioPropertyValue]:
    if values is None:
        return {}

    result: dict[str, ScenarioPropertyValue] = {}
    for value in values:
        if "=" not in value:
            raise typer.BadParameter("Property overrides must use key=value format.", param_hint="--property")
        key, raw_value = value.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter("Property overrides must include a property key.", param_hint="--property")
        existing = result.get(key)
        if existing is None:
            result[key] = raw_value
        elif isinstance(existing, list):
            existing.append(raw_value)
        elif isinstance(existing, str):
            result[key] = [existing, raw_value]
        else:
            raise typer.BadParameter(
                f"Property override for {key} was parsed into an unexpected type.", param_hint="--property"
            )
    return result


def _fetch_arcadia_tariffs(
    *,
    master_tariff_id: int,
    effective_on: date,
    populate_rates: bool,
) -> list[tariff.TariffExtended]:
    api = ArcadiaSignalAPI()
    return list(
        api.tariffs.iter_pages(
            fields="ext",
            master_tariff_id=master_tariff_id,
            effective_on=effective_on,
            populate_properties=True,
            populate_rates=populate_rates,
        )
    )


def _fetch_openei_tariffs(
    *,
    eia_id: int,
    sector: UtilityRateSector,
    detail: str,
    effective_on: date,
) -> list[UtilityRatesResponseItem]:
    api_key = os.getenv("OPENEI_API_KEY")
    if not api_key:
        raise ValueError("API Key is not set (via OPENEI_API_KEY variable)")
    with console.status("Fetching rates..."):
        return list(
            iter_utility_rates(
                api_key,
                effective_on_date=datetime.combine(effective_on, datetime.min.time(), tzinfo=UTC),
                sector=sector,
                detail=cast(Literal["full", "minimal"], detail),
                eia=eia_id,
            )
        )


def _print_arcadia_properties(tariffs: list[tariff.TariffExtended]) -> None:
    property_rows = _collect_arcadia_property_rows(tariffs)

    if not property_rows:
        console.print("[yellow]No Arcadia properties found for this tariff.[/yellow]")
        return

    table = Table(title="Arcadia tariff properties")
    table.add_column("Key")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Description")
    table.add_column("Choices")
    for key_name, (display_name, data_type, description, choices) in sorted(property_rows.items()):
        table.add_row(key_name, display_name, data_type, description, choices)
    console.print(table)


def _collect_arcadia_property_rows(tariffs: list[tariff.TariffExtended]) -> dict[str, tuple[str, str, str, str]]:
    property_rows: dict[str, dict[str, str | dict[str, str]]] = {}

    for tariff_ in tariffs:
        for prop in tariff_.get("properties", []):
            key_name = prop["key_name"]
            if key_name == "chargeClass":
                continue
            row = property_rows.setdefault(
                key_name,
                {
                    "display_name": prop["display_name"],
                    "data_type": prop["data_type"],
                    "description": prop["description"],
                    "choices_by_value": {},
                },
            )
            choices_by_value = cast(dict[str, str], row["choices_by_value"])
            for choice in prop.get("choices", []):
                _ = choices_by_value.setdefault(choice["value"], choice["display_value"])

    return {key_name: _format_arcadia_property_row(row) for key_name, row in property_rows.items()}


def _format_arcadia_property_row(row: dict[str, str | dict[str, str]]) -> tuple[str, str, str, str]:
    choices_by_value = cast(dict[str, str], row["choices_by_value"])
    choices = ", ".join(f"{display_value}={value}" for value, display_value in sorted(choices_by_value.items()))
    return (
        cast(str, row["display_name"]),
        cast(str, row["data_type"]),
        cast(str, row["description"]),
        choices,
    )


def _get_cached_utility_sales_parquet(now: datetime | None = None) -> Path:
    logger = logging.getLogger(__name__)
    current_time = now or datetime.now()
    UTILITY_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if _is_fresh_cache(UTILITY_CACHE_PATH, current_time):
        logger.debug("Using cached utility parquet at %s", UTILITY_CACHE_PATH)
        return UTILITY_CACHE_PATH

    try:
        _download_utility_sales_parquet(UTILITY_CACHE_PATH)
    except Exception:
        if UTILITY_CACHE_PATH.exists():
            logger.warning(
                "Failed to refresh utility parquet cache; falling back to stale cache at %s",
                UTILITY_CACHE_PATH,
                exc_info=True,
            )
            return UTILITY_CACHE_PATH
        raise

    logger.debug("Refreshed utility parquet cache at %s", UTILITY_CACHE_PATH)
    return UTILITY_CACHE_PATH


def _is_fresh_cache(path: Path, now: datetime) -> bool:
    if not path.exists():
        return False
    age_seconds = now.timestamp() - path.stat().st_mtime
    return age_seconds < UTILITY_CACHE_TTL_SECONDS


def _download_utility_sales_parquet(destination: Path) -> None:
    with (
        cast(BinaryIO, urlopen(CORE_EIA861_YEARLY_SALES_HTTPS)) as response,
        NamedTemporaryFile(dir=destination.parent, delete=False) as temporary_file,
    ):
        shutil.copyfileobj(response, temporary_file)
        temp_path = Path(temporary_file.name)
    _ = temp_path.replace(destination)


def _is_valid_year(value: str) -> bool:
    try:
        _ = date(int(value), 1, 1)
    except (TypeError, ValueError):
        return False
    return True


if __name__ == "__main__":
    main_cli()
