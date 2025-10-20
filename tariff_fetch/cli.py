from typing import Annotated

import typer
from rich.prompt import Prompt

STATE_CHOICES = [
    state.lower()
    for state in [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    ]
]


def main(state: Annotated[str | None, typer.Argument(help="Two-letter state abbreviation")] = None):
    state_ = state or Prompt.ask(
        "Enter two-letter state abbreviation", choices=STATE_CHOICES, show_choices=False, case_sensitive=False
    )
    if state_.lower() not in STATE_CHOICES:
        raise ValueError(f'Invalid value for state: "{state}"')


if __name__ == "__main__":
    typer.run(main)
