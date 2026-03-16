"""Direct CLI for converting one Arcadia master tariff to URDB."""

import json
import logging
import os
from pathlib import Path
from typing import Annotated, cast, get_args

import requests
import typer
from dotenv import load_dotenv
from rich.logging import RichHandler

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.exception import ConversionCancelled
from tariff_fetch.urdb.arcadia.scenario import Scenario

from ._cli import console

FORMAT = "%(message)s"

DEFAULT_CHARGE_CLASSES: tuple[RateChargeClass, ...] = (
    "DISTRIBUTION",
    "SUPPLY",
    "TRANSMISSION",
    "OTHER",
    "CONTRACTED",
)
ALL_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()], force=True)


def _print_error(
    message: str, *, code: int = 1, json_errors: bool = False, extra: dict[str, str | int] | None = None
) -> None:
    if json_errors:
        payload: dict[str, str | int] = {"error": message, "exit_code": code}
        if extra:
            payload.update(extra)
        console.print_json(json.dumps(payload))
    else:
        console.print(f"[red]{message}[/]")
    raise typer.Exit(code=code)


def _require_arcadia_credentials(*, json_errors: bool) -> None:
    missing = [name for name in ("ARCADIA_APP_ID", "ARCADIA_APP_KEY") if not os.getenv(name)]
    if missing:
        message = f"Missing required environment variables: {', '.join(missing)}"
        _print_error(message, json_errors=json_errors, extra={"provider": "arcadia"})


def _http_error_message(exc: requests.HTTPError) -> str:
    message = str(exc).strip()
    if message:
        return message
    if exc.response is not None:
        return f"Arcadia request failed with status {exc.response.status_code}"
    return "Arcadia request failed"


def main(
    master_tariff_id: Annotated[int, typer.Argument(help="Arcadia master tariff id to convert")],
    year: Annotated[int, typer.Argument(help="Calendar year to convert")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Path to write the converted URDB JSON"),
    ] = None,
    apply_percentages: Annotated[
        bool,
        typer.Option("--apply-percentages/--no-apply-percentages", help="Apply supported percentage rates"),
    ] = False,
    charge_classes: Annotated[
        list[str] | None,
        typer.Option("--charge-class", help="Arcadia charge class to include; repeat to include multiple"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists"),
    ] = False,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Raise conversion errors immediately instead of prompting to continue"),
    ] = False,
    json_errors: Annotated[
        bool,
        typer.Option("--json-errors", help="Emit machine-readable JSON errors"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable debug logging"),
    ] = False,
) -> None:
    """Convert one Arcadia master tariff to a URDB JSON file."""

    _configure_logging(verbose)
    _ = load_dotenv()
    _require_arcadia_credentials(json_errors=json_errors)

    output_path = output or Path(f"./outputs/arcadia_urdb_{master_tariff_id}_{year}.json")
    if output_path.exists() and not force:
        _print_error(
            f"Output file already exists: {output_path}. Pass --force to overwrite it.",
            json_errors=json_errors,
            extra={"path": output_path.as_posix()},
        )

    scenario_charge_classes = _parse_charge_classes(charge_classes)
    scenario = Scenario(
        master_tariff_id=master_tariff_id,
        year=year,
        apply_percentages=apply_percentages,
        charge_classes=scenario_charge_classes,
    )
    api = ArcadiaSignalAPI()

    if not json_errors:
        console.print("Converting Arcadia tariff to URDB...")
    try:
        result = build_urdb(api, scenario, interactive_errors=not fail_fast)
    except requests.HTTPError as exc:
        extra: dict[str, str | int] = {"provider": "arcadia"}
        if exc.response is not None:
            extra["status_code"] = exc.response.status_code
        _print_error(_http_error_message(exc), json_errors=json_errors, extra=extra)
    except ConversionCancelled as exc:
        _print_error(str(exc), json_errors=json_errors, extra={"provider": "arcadia"})
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _ = output_path.write_text(json.dumps(result, indent=2))
        console.print(f"Wrote URDB tariff to [blue]{output_path}[/]")


def main_cli() -> None:
    """Run the direct Arcadia-to-URDB CLI."""

    typer.run(main)


def _parse_charge_classes(charge_classes: list[str] | None) -> set[RateChargeClass]:
    if charge_classes is None:
        return set(DEFAULT_CHARGE_CLASSES)

    normalized = [charge_class.strip().upper() for charge_class in charge_classes]
    invalid = sorted(set(normalized) - set(ALL_CHARGE_CLASSES))
    if invalid:
        allowed = ", ".join(ALL_CHARGE_CLASSES)
        console.print(f"[red]Invalid charge classes:[/] {', '.join(invalid)}")
        console.print(f"Allowed values: {allowed}")
        raise typer.Exit(code=1)
    return {cast(RateChargeClass, charge_class) for charge_class in normalized}


if __name__ == "__main__":
    main_cli()
