import json
import logging
import shutil
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, BinaryIO, cast, get_args
from urllib.request import urlopen

import polars as pl
import typer
from dotenv import load_dotenv
from platformdirs import user_cache_dir
from rich.logging import RichHandler
from rich.prompt import Prompt

from tariff_fetch._cli.arcadia_urdb import process_genability as process_genability_urdb
from tariff_fetch._cli.genability import process_genability
from tariff_fetch._cli.openei import process_openei
from tariff_fetch._cli.rateacuity import process_rateacuity, process_rateacuity_gas
from tariff_fetch._cli.rateacuity_gas_urdb import process_rateacuity_gas_urdb
from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.rateacuity.base import AuthorizationError
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.scenario import Scenario

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
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    if ctx.invoked_subcommand is not None:
        return
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
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
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
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Raise conversion errors immediately instead of prompting to continue"),
    ] = False,
):
    if ctx.invoked_subcommand is not None:
        return
    state_ = state or prompt_state().value
    output_folder_ = Path(output_folder)
    log_path = _configure_logging(
        "tariff_fetch_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    utility = prompt_utility(state_)
    year = prompt_year() if year is None else year

    console.print(f"Logging to [blue]{log_path}[/]")
    console.print("Processing [blue]Genability[/]")
    try:
        process_genability_urdb(
            utility=utility, output_folder=output_folder_, year=year, interactive_errors=not fail_fast
        )
    except typer.Exit as e:
        _handle_expected_exit(e)
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise typer.Exit(1) from e


@urdb_app.command("ni", help="Convert a specific Arcadia master tariff directly to URDB JSON.")
def urdb_direct(
    master_tariff_id: Annotated[int, typer.Argument(help="Arcadia master tariff id to convert")],
    year: Annotated[int, typer.Argument(help="Calendar year to convert")],
    charge_classes: Annotated[
        list[str] | None,
        typer.Option("--charge-class", help="Arcadia charge class to include; repeat to include multiple"),
    ] = None,
    apply_percentages: Annotated[
        bool,
        typer.Option("--apply-percentages/--no-apply-percentages", help="Apply supported percentage rates"),
    ] = True,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Raise conversion errors immediately instead of prompting to continue"),
    ] = False,
    log_level: Annotated[
        LogLevel, typer.Option("--log-level", help="Logging level", case_sensitive=False)
    ] = LogLevel.INFO,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Path to write the converted URDB JSON")] = None,
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
):
    _ = load_dotenv()
    if output is None:
        output = Path("./outputs")
        output.mkdir(parents=True, exist_ok=True)
    if output.is_dir():
        output = output / f"arcadia_urdb_{master_tariff_id}_{year}.json"
    if output.exists() and not force:
        console.print(f"[red]Output file already exists: {output}. Pass --force to overwrite it.[/red]")
        raise typer.Exit(1)
    log_path = _configure_logging(
        "tariff_fetch_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output.parent / "logs"),
        log_file=log_file,
    )
    console.print(f"Logging to [blue]{log_path}[/]")
    scenario_charge_classes = _parse_charge_classes(charge_classes)
    scenario = Scenario(
        master_tariff_id=master_tariff_id,
        year=year,
        apply_percentages=apply_percentages,
        charge_classes=scenario_charge_classes,
    )
    api = ArcadiaSignalAPI()
    try:
        result = build_urdb(api, scenario, interactive_errors=not fail_fast)
    except typer.Exit as e:
        _handle_expected_exit(e)
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise typer.Exit(code=1) from e
    else:
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
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    if ctx.invoked_subcommand is not None:
        return

    state_ = (state or prompt_state()).value
    output_folder_ = Path(output_folder)
    log_path = _configure_logging(
        "tariff_fetch_gas",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    console.print(f"Logging to [blue]{log_path}[/]")
    try:
        process_rateacuity_gas(output_folder_, state_)
    except AuthorizationError:
        console.print("Authorization failed")
        console.print(
            "Check if credentials provided via [b]RATEACUITY_USERNAME[/] and [b]RATEACUITY_PASSWORD[/] environment variables are correct"
        )


@gas_app.command("urdb", help="Convert RateAcuity gas tariffs to URDB format.")
def main_gas_urdb(
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
    log_dir: Annotated[Path | None, typer.Option("--log-dir", help="Directory to write logs to")] = None,
    log_file: Annotated[Path | None, typer.Option("--log-file", help="File path to write logs to")] = None,
):
    state_ = (state or prompt_state()).value
    output_folder_ = Path(output_folder)
    year_ = prompt_year() if year is None else year
    log_path = _configure_logging(
        "tariff_fetch_gas_urdb",
        log_level=_log_level_to_int(log_level),
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    console.print(f"Logging to [blue]{log_path}[/]")
    try:
        process_rateacuity_gas_urdb(output_folder_, state_, year_)
    except AuthorizationError:
        console.print("Authorization failed")
        console.print(
            "Check if credentials provided via [b]RATEACUITY_USERNAME[/] and [b]RATEACUITY_PASSWORD[/] environment variables are correct"
        )


@cache_app.command("clear", help="Delete the cached EIA utility parquet file.")
def clear_cache():
    if not UTILITY_CACHE_PATH.exists():
        console.print(f"No cached utilities parquet found at [blue]{UTILITY_CACHE_PATH}[/]")
        return

    UTILITY_CACHE_PATH.unlink()
    console.print(f"Cleared cached utilities parquet at [blue]{UTILITY_CACHE_PATH}[/]")


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
    log_path = _configure_logging(
        "tariff_fetch",
        log_level=log_level,
        log_dir=log_dir or (output_folder_ / "logs"),
        log_file=log_file,
    )
    console.print(f"Logging to [blue]{log_path}[/]")
    utility = prompt_utility(state_)

    match provider:
        case Provider.GENABILITY:
            console.print("Processing [blue]Genability[/]")
            try:
                process_genability(utility=utility, output_folder=output_folder_, effective_on=effective_date)
            except typer.Exit as e:
                _handle_expected_exit(e)
            except Exception as e:
                logging.getLogger(__name__).exception(e)
                raise typer.Exit(1) from e
        case Provider.OPENEI:
            console.print("Processing [blue]OpenEI[/]")
            try:
                process_openei(utility, output_folder_, effective_on=effective_date)
            except typer.Exit as e:
                _handle_expected_exit(e)
            except Exception as e:
                logging.getLogger(__name__).exception(e)
                raise typer.Exit(1) from e
        case Provider.RATEACUITY:
            try:
                process_rateacuity(output_folder_, state_, utility)
            except typer.Exit as e:
                _handle_expected_exit(e)
            except Exception as e:
                logging.getLogger(__name__).exception(e)
                raise typer.Exit(1) from e


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
    entity_type_header = "Entity Type"
    sales_header = "Sales (MWh)"
    revenue_header = "Revenue ($)"
    customers_header = "Customers"

    largest_utility_name = max(len(utility_name_header), *(len(row["utility_name"]) for row in rows))  # pyright: ignore[reportAny]
    largest_entity_type = max(len(entity_type_header), *(len(row["entity_type"][:18]) for row in rows))  # pyright: ignore[reportAny]
    largest_sales_col = max(len(sales_header), *(len(fmt_number(row["sales_mwh"])) for row in rows))  # pyright: ignore[reportAny]
    largest_revenue_col = max(len(revenue_header), *(len(fmt_number(row["sales_revenue"])) for row in rows))  # pyright: ignore[reportAny]
    largest_customers_col = max(len(customers_header), *(len(fmt_number(row["customers"])) for row in rows))  # pyright: ignore[reportAny]

    header_str_utility_name = utility_name_header.ljust(largest_utility_name)
    header_str_entity_type = entity_type_header.ljust(largest_entity_type)
    header_str_sales = sales_header.ljust(largest_sales_col)
    header_str_revenue = revenue_header.ljust(largest_revenue_col)
    header_str_customers = customers_header.ljust(largest_customers_col)
    header_str = f"{header_str_utility_name} | {header_str_entity_type} | {header_str_sales} | {header_str_revenue} | {header_str_customers}"
    separator = q.Separator(line="-" * len(header_str))

    header = q.Choice[Utility | None](
        title=header_str,
        value=None,
    )

    def build_choice(row: dict[str, str | int | float | None]) -> q.Choice[Utility | None]:
        name_col = cast(str, row["utility_name"]).ljust(largest_utility_name)
        entity_type = (cast(str, row["entity_type"]) or "-")[:18].ljust(largest_entity_type)
        sales_col = fmt_number(cast(float, row["sales_mwh"])).ljust(largest_sales_col)
        revenue_col = fmt_number(cast(float, row["sales_revenue"])).ljust(largest_revenue_col)
        customers_col = fmt_number(cast(float, row["customers"])).ljust(largest_customers_col)
        title = f"{name_col} | {entity_type} | {sales_col} | {revenue_col} | {customers_col}"
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


def prompt_year() -> int:
    result = q.text("Enter year", default=str(date.today().year - 1), validate=_is_valid_year).ask_or_exit()
    return int(result)


def prompt_state() -> StateCode:
    choice = Prompt.ask(
        "Enter two-letter state abbreviation",
        choices=[state.value for state in StateCode],
        show_choices=False,
        case_sensitive=False,
    )
    return StateCode(choice.lower())


def _parse_charge_classes(charge_classes: list[str] | None) -> set[RateChargeClass]:
    if charge_classes is None:
        return set(ALL_CHARGE_CLASSES)

    normalized = [charge_class.strip().upper() for charge_class in charge_classes]
    invalid = sorted(set(normalized) - set(ALL_CHARGE_CLASSES))
    if invalid:
        allowed = ", ".join(ALL_CHARGE_CLASSES)
        console.print(f"[red]Invalid charge classes:[/] {', '.join(invalid)}")
        console.print(f"Allowed values: {allowed}")
        raise typer.Exit(code=1)
    return {cast(RateChargeClass, charge_class) for charge_class in normalized}


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
