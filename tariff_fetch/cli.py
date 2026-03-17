import logging
from datetime import date
from pathlib import Path
from typing import Annotated, cast

import polars as pl
import questionary
import typer
from requests import HTTPError
from rich.prompt import Prompt

from tariff_fetch._cli.arcadia_urdb import process_genability as process_genability_urdb
from tariff_fetch._cli.genability import process_genability
from tariff_fetch._cli.openei import process_openei
from tariff_fetch._cli.rateacuity import process_rateacuity
from tariff_fetch.rateacuity.base import AuthorizationError

from ._cli import console
from ._cli.types import Provider, StateCode, Utility

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

ENTITY_TYPES_SORTORDER = ["Investor Owned", "Cooperative", "Municipal"]
CORE_EIA861_YEARLY_SALES_HTTPS = (
    "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_eia861__yearly_sales.parquet"
)


@app.command("urdb")
def main_urdb(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
    year: Annotated[int | None, typer.Option("--year", "-y")] = None,
):
    logging.basicConfig(level=logging.DEBUG)
    state_ = state or prompt_state().value
    output_folder_ = Path(output_folder)
    utility = prompt_utility(state_)
    year = prompt_year()

    console.print("Processing [blue]Genability[/]")
    try:
        process_genability_urdb(utility=utility, output_folder=output_folder_, year=year)
    except HTTPError as e:
        if e.response.status_code == 401:
            console.print("Authorization failed")
            console.print(
                "Check if credentials set via [b]ARCADIA_APP_ID[/] and [b]ARCADIA_APP_KEY[/] environment variables are correct"
            )
        else:
            raise


@app.command("raw")
def main_raw(
    state: Annotated[
        StateCode | None, typer.Option("--state", "-s", help="Two-letter state abbreviation", case_sensitive=False)
    ] = None,
    provider: Annotated[Provider | None, typer.Option("--provider", "-p", case_sensitive=False)] = None,
    output_folder: Annotated[
        str, typer.Option("--output-folder", "-o", help="Folder to store outputs in")
    ] = "./outputs",
):
    logging.basicConfig(level=logging.DEBUG)
    state_ = state or prompt_state().value
    provider = provider or prompt_provider()
    output_folder_ = Path(output_folder)
    utility = prompt_utility(state_)

    match provider:
        case Provider.GENABILITY:
            console.print("Processing [blue]Genability[/]")
            try:
                process_genability(utility=utility, output_folder=output_folder_)
            except HTTPError as e:
                if e.response.status_code == 401:
                    console.print("Authorization failed")
                    console.print(
                        "Check if credentials set via [b]ARCADIA_APP_ID[/] and [b]ARCADIA_APP_KEY[/] environment variables are correct"
                    )
                else:
                    raise
        case Provider.OPENEI:
            console.print("Processing [blue]OpenEI[/]")
            try:
                process_openei(utility, output_folder_)
            except HTTPError as e:
                if e.response.status_code == 403:
                    console.print("Authorization failed")
                    console.print("Check if [b]OPENEI_API_KEY[/] environment variable is correct")
                else:
                    raise
        case Provider.RATEACUITY:
            console.print("Processing [blue]RateAcuity[/]")
            try:
                process_rateacuity(output_folder_, state_, utility)
            except AuthorizationError:
                console.print("Authorization failed")
                console.print(
                    "Check if credentials provided via [b]RATEACUITY_USERNAME[/] and [b]RATEACUITY_PASSWORD[/] environment variables are correct"
                )


def main_cli():
    app()


def prompt_provider() -> Provider:
    return cast(
        Provider,
        questionary.select(
            message="Select provider",
            choices=[questionary.Choice(title=_.value, value=_) for _ in Provider],
        ).ask(),
    )


def prompt_utility(state: str) -> Utility:
    with console.status("Fetching utilities..."):
        yearly_sales_df = (
            pl.read_parquet(CORE_EIA861_YEARLY_SALES_HTTPS)  # pyright: ignore[reportUnknownMemberType]
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
    separator = questionary.Separator(line="-" * len(header_str))

    header = questionary.Choice(
        title=header_str,
        value=0,
    )

    def build_choice(row: dict[str, str | int | float | None]) -> questionary.Choice:
        name_col = cast(str, row["utility_name"]).ljust(largest_utility_name)
        entity_type = (cast(str, row["entity_type"]) or "-")[:18].ljust(largest_entity_type)
        sales_col = fmt_number(cast(float, row["sales_mwh"])).ljust(largest_sales_col)
        revenue_col = fmt_number(cast(float, row["sales_revenue"])).ljust(largest_revenue_col)
        customers_col = fmt_number(cast(float, row["customers"])).ljust(largest_customers_col)
        title = f"{name_col} | {entity_type} | {sales_col} | {revenue_col} | {customers_col}"
        return questionary.Choice(
            title=title,
            value=Utility(eia_id=cast(int, row["utility_id_eia"]), name=cast(str, row["utility_name"])),
        )

    result = 0
    while result == 0:
        result = cast(
            Utility,
            questionary.select(
                message="Select a utility",
                choices=[header, separator, *[build_choice(row) for row in rows]],
                use_search_filter=True,
                use_jk_keys=False,
                use_shortcuts=False,
            ).ask(),
        )
    return result


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


def prompt_state() -> StateCode:
    choice = Prompt.ask(
        "Enter two-letter state abbreviation",
        choices=[state.value for state in StateCode],
        show_choices=False,
        case_sensitive=False,
    )
    return StateCode(choice.lower())


if __name__ == "__main__":
    main_cli()
