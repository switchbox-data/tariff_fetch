from pathlib import Path
from typing import Annotated

import polars as pl
import questionary
import typer
from rich.prompt import Prompt

from tariff_fetch._cli.genability import process_genability
from tariff_fetch._cli.openei import process_openei
from tariff_fetch._cli.rateacuity import process_rateacuity
from tariff_fetch.openeia import CORE_EIA861_Yearly_Sales

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
        yearly_sales_df = (
            pl.read_parquet(CORE_EIA861_Yearly_Sales.https)
            .filter(pl.col("state") == state.upper())
            .filter(pl.col("report_date") == pl.col("report_date").max().over("utility_id_eia"))
            .group_by("utility_id_eia")
            .agg(
                pl.col("utility_name_eia").last().alias("utility_name"),
                pl.col("business_model").last().alias("business_model"),
                pl.col("sales_mwh").sum().alias("sales_mwh"),
                pl.col("sales_revenue").sum().alias("sales_revenue"),
                pl.col("customers").sum().alias("customers"),
            )
            .sort("utility_name")
        )

    def fmt_number(value: float | int | None) -> str:
        if value is None:
            return "-"
        return f"{value:,.0f}"

    header = questionary.Separator(
        "Utility Name                                 | Model        |  Sales (MWh) | Revenue ($) | Customers",
    )

    def build_choice(row: dict) -> questionary.Choice:
        business_model_raw = row.get("business_model") or "-"
        name_col = f"{row['utility_name']:<44}"
        model_col = f"{business_model_raw:<12}"
        sales_col = f"{fmt_number(row.get('sales_mwh')):>12}"
        revenue_col = f"{fmt_number(row.get('sales_revenue')):>11}"
        customers_col = f"{fmt_number(row.get('customers')):>9}"
        title = f"{name_col} | {model_col} | {sales_col} | {revenue_col} | {customers_col}"
        return questionary.Choice(
            title=title,
            value=Utility(eia_id=row["utility_id_eia"], name=row["utility_name"]),
        )

    return questionary.select(
        message="Select a utility",
        choices=[header, *[build_choice(row) for row in yearly_sales_df.iter_rows(named=True)]],
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
        console.print("Processing [blue]Genability[/]")
        process_genability(utility=utility, output_folder=output_folder_)
    if Provider.OPENEI in providers_:
        console.print("Processing [blue]OpenEI[/]")
        process_openei(utility, output_folder_)
    if Provider.RATEACUITY in providers_:
        console.print("Processing [blue]RateAcuity[/]")
        process_rateacuity(output_folder_, state_, utility)


if __name__ == "__main__":
    typer.run(main)
