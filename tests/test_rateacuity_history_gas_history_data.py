import pytest

from tariff_fetch.urdb.rateacuity_history_gas.history_data import (
    DayOfMonth,
    RowValidationError,
    Season,
    _row_to_model,
)


def _base_row() -> dict[str, object]:
    row: dict[str, object] = {
        "rate": "Supply",
        "season": None,
        "effective_date": None,
        "start": None,
        "end": None,
        "determinant": None,
        "location": None,
        "rate_determinant": "per month",
    }
    for month in range(1, 13):
        row[f"{month:02d}/01/2025"] = 1.0
    return row


def test_row_to_model_parses_season_string() -> None:
    row = _base_row()
    row["season"] = "11/01 - 04/30"

    result = _row_to_model(row, location_avg_factor=1, month_column_names=list(row.keys())[-12:])

    assert result.season == Season(
        start=DayOfMonth(day=1, month=11),
        end=DayOfMonth(day=30, month=4),
    )


def test_row_to_model_rejects_invalid_season_string() -> None:
    row = _base_row()
    row["season"] = "winter"

    with pytest.raises(RowValidationError):
        _row_to_model(row, location_avg_factor=1, month_column_names=list(row.keys())[-12:])


@pytest.mark.parametrize("season", ["13/01 - 04/30", "00/15 - 01/01", "02/30 - 03/01", "04/31 - 05/01"])
def test_row_to_model_rejects_impossible_season_dates(season: str) -> None:
    row = _base_row()
    row["season"] = season

    with pytest.raises(RowValidationError):
        _row_to_model(row, location_avg_factor=1, month_column_names=list(row.keys())[-12:])


def test_row_to_model_allows_february_29_season_boundary() -> None:
    row = _base_row()
    row["season"] = "02/29 - 03/01"

    result = _row_to_model(row, location_avg_factor=1, month_column_names=list(row.keys())[-12:])

    assert result.season == Season(
        start=DayOfMonth(day=29, month=2),
        end=DayOfMonth(day=1, month=3),
    )
