from pathlib import Path
from typing import Annotated

import polars as pl
import questionary
import typer
from rich.prompt import Prompt

from tariff_fetch._cli.genability import process_genability
from tariff_fetch._cli.openei import process_openei
from tariff_fetch._cli.rateacuity import process_rateacuity
from tariff_fetch.openeia import Core_PUDL_ASSN_EIA_PUDL_UTILITIES, CoreEIA861_ASSN_UTILITY

from ._cli import console
from ._cli.types import Provider, StateCode, Utility


def prompt_state() -> StateCode:
    choice = Prompt.ask(
        "Enter two-letter state abbreviation",
        choices=[state.value for state in StateCode],
        show_choices=False,
        case_sensitive=False,
    )
    return StateCode(choice.lower())


def prompt_providers() -> list[Provider]:
    return questionary.checkbox(
        message="Select providers",
        choices=[questionary.Choice(title=_.value, value=_) for _ in Provider],
        validate=lambda x: True if x else "Select at least one provider",
    ).ask()


def prompt_utility(state: str) -> Utility:
    with console.status("Fetching utilities..."):
        eia861_df = (
            pl.read_parquet(CoreEIA861_ASSN_UTILITY.https)
            .filter(pl.col("state") == state.upper())
            .filter(pl.col("report_date") == pl.col("report_date").max().over("utility_id_eia"))
            .group_by(pl.col("utility_id_eia"))
            .agg(pl.col("report_date"))
        )
        eiaids_in_state = [_[0] for _ in eia861_df.iter_rows()]

        utilities_df = pl.read_parquet(Core_PUDL_ASSN_EIA_PUDL_UTILITIES.https).filter(
            pl.col("utility_id_eia").is_in(eiaids_in_state)
        )

        utilities = [
            Utility(
                row["utility_id_eia"],
                row["utility_name_eia"],
            )
            for row in utilities_df.iter_rows(named=True)
        ]

    return questionary.select(
        message="Select a utility",
        choices=[questionary.Choice(title=utility.name, value=utility) for utility in utilities],
        use_search_filter=True,
        use_jk_keys=False,
        use_shortcuts=False,
    ).ask()


def main(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    providers: Annotated[list[Provider] | None, typer.Option("--providers", "-p", case_sensitive=False)] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
):
    # print(pl.read_parquet(CoreEIA861_ASSN_UTILITY.https))
    if (state_ := (state or prompt_state()).value) is None:
        return
    if (providers_ := providers or prompt_providers()) is None:
        return
    output_folder_ = Path(output_folder)
    if (utility := prompt_utility(state_)) is None:
        return
    if Provider.GENABILITY in providers_:
        console.print("Processing Genability")
        process_genability(utility=utility, output_folder=output_folder_)
    if Provider.OPENEI in providers_:
        console.print("Processing OpenEI")
        process_openei(utility, output_folder_)
    if Provider.RATEACUITY in providers_:
        console.print("Processing RateAcuity")
        process_rateacuity(output_folder_, state_, utility)


if __name__ == "__main__":
    typer.run(main)
