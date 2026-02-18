from datetime import date
from pathlib import Path
from typing import Annotated, cast

import questionary
import rich
import typer
from rich.prompt import Prompt

from tariff_fetch._cli.rateacuity import process_rateacuity_gas
from tariff_fetch._cli.rateacuity_gas_urdb import process_rateacuity_gas_urdb
from tariff_fetch.rateacuity.base import AuthorizationError

from ._cli.types import StateCode


def prompt_state() -> StateCode:
    choice = Prompt.ask(
        "Enter two-letter state abbreviation",
        choices=[state.value for state in StateCode],
        show_choices=False,
        case_sensitive=False,
    )
    return StateCode(choice.lower())


def prompt_year() -> int:
    result = cast(
        str, questionary.text("Enter year", default=str(date.today().year - 1), validate=_is_valid_year).ask()
    )
    return int(result)


def _is_valid_year(value: str) -> bool:
    try:
        _ = date(int(value), 1, 1)
    except (TypeError, ValueError):
        return False
    return True


def main(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    urdb: bool = False,
):
    # print(pl.read_parquet(CoreEIA861_ASSN_UTILITY.https))
    state_ = (state or prompt_state()).value
    output_folder_ = Path(output_folder)
    try:
        if urdb:
            year = prompt_year()
            process_rateacuity_gas_urdb(output_folder_, state_, year)
        else:
            process_rateacuity_gas(output_folder_, state_)
    except AuthorizationError:
        rich.print("Authorization failed")
        rich.print(
            "Check if credentials provided via [b]RATEACUITY_USERNAME[/] and [b]RATEACUITY_PASSWORD[/] environment variables are correct"
        )


def main_cli():
    typer.run(main)


if __name__ == "__main__":
    main_cli()
