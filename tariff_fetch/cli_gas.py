from pathlib import Path
from typing import Annotated

import typer
from rich.prompt import Prompt

from tariff_fetch._cli.rateacuity import process_rateacuity_gas

from ._cli.types import StateCode


def prompt_state() -> StateCode:
    choice = Prompt.ask(
        "Enter two-letter state abbreviation",
        choices=[state.value for state in StateCode],
        show_choices=False,
        case_sensitive=False,
    )
    return StateCode(choice.lower())


def main(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
):
    # print(pl.read_parquet(CoreEIA861_ASSN_UTILITY.https))
    if (state_ := (state or prompt_state()).value) is None:
        return
    output_folder_ = Path(output_folder)
    process_rateacuity_gas(output_folder_, state_)


if __name__ == "__main__":
    typer.run(main)
