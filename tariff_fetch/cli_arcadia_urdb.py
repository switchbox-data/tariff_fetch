"""Direct CLI for converting one Arcadia master tariff to URDB."""

import json
import logging
import os
from pathlib import Path
from typing import Annotated, cast, get_args

import typer
from dotenv import load_dotenv
from rich.logging import RichHandler

from tariff_fetch.arcadia.api import ArcadiaSignalAPI
from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.urdb.arcadia.build import build_urdb
from tariff_fetch.urdb.arcadia.scenario import Scenario

from ._cli import console

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

DEFAULT_CHARGE_CLASSES: tuple[RateChargeClass, ...] = (
    "DISTRIBUTION",
    "SUPPLY",
    "TRANSMISSION",
    "OTHER",
    "CONTRACTED",
)
ALL_CHARGE_CLASSES = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))


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
) -> None:
    """Convert one Arcadia master tariff to a URDB JSON file."""

    _ = load_dotenv()
    if not os.getenv("ARCADIA_APP_ID"):
        console.print("[b]ARCADIA_APP_ID[/] environment variable is not set.")
    if not os.getenv("ARCADIA_APP_KEY"):
        console.print("[b]ARCADIA_APP_KEY[/] environment variable is not set.")
    if not (os.getenv("ARCADIA_APP_ID") and os.getenv("ARCADIA_APP_KEY")):
        raise typer.Exit(code=1)

    output_path = output or Path(f"./outputs/arcadia_urdb_{master_tariff_id}_{year}.json")
    if output_path.exists() and not force:
        console.print(f"[red]Output file already exists:[/] {output_path}")
        console.print("Pass [b]--force[/] to overwrite it.")
        raise typer.Exit(code=1)

    scenario_charge_classes = _parse_charge_classes(charge_classes)
    scenario = Scenario(
        master_tariff_id=master_tariff_id,
        year=year,
        apply_percentages=apply_percentages,
        charge_classes=scenario_charge_classes,
    )
    api = ArcadiaSignalAPI()

    console.print("Converting Arcadia tariff to URDB...")
    result = build_urdb(api, scenario)

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
