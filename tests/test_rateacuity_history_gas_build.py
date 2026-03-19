import pytest

from tariff_fetch.urdb.rateacuity_history_gas import (
    _build_energy_schedule_raw,
    _build_static_charges,
    _get_monthly_taxes,
    _seasonal_month_fraction,
)
from tariff_fetch.urdb.rateacuity_history_gas.history_data import (
    ConsumptionRow,
    DayOfMonth,
    FixedChargeRow,
    PercentageRow,
    Season,
)
from tariff_fetch.urdb.rateacuity_history_gas.shared import kwh_multiplier


def test_seasonal_month_fraction_handles_partial_wraparound_seasons() -> None:
    season = Season(
        start=DayOfMonth(day=15, month=11),
        end=DayOfMonth(day=10, month=4),
    )

    assert _seasonal_month_fraction(season, 2025, 9) == 0
    assert _seasonal_month_fraction(season, 2025, 10) == pytest.approx(16 / 30)
    assert _seasonal_month_fraction(season, 2025, 11) == 1
    assert _seasonal_month_fraction(season, 2025, 3) == pytest.approx(10 / 30)
    assert _seasonal_month_fraction(season, 2025, 4) == 0


def test_seasonal_month_fraction_uses_actual_year_for_leap_february() -> None:
    season = Season(
        start=DayOfMonth(day=1, month=2),
        end=DayOfMonth(day=29, month=2),
    )

    assert _seasonal_month_fraction(season, 2024, 1) == 1
    assert _seasonal_month_fraction(season, 2025, 1) == pytest.approx(28 / 28)


def test_build_helpers_prorate_percentage_and_fixed_rows_by_season() -> None:
    season = Season(
        start=DayOfMonth(day=15, month=11),
        end=DayOfMonth(day=10, month=12),
    )
    percentage_row = PercentageRow(
        rate="Tax",
        season=season,
        year=2025,
        effective_date=None,
        month_values=[10.0] * 12,
        location_avg_factor=1,
        rate_determinant="percent",
    )
    fixed_row = FixedChargeRow(
        rate="Customer Charge",
        season=season,
        year=2025,
        effective_date=None,
        month_values=[30.0] * 12,
        location_avg_factor=1,
        rate_determinant="per month",
    )

    monthly_taxes = _get_monthly_taxes([percentage_row])
    static_charges = _build_static_charges([fixed_row])
    fixed_charge = static_charges.get("fixedchargefirstmeter")

    assert monthly_taxes[9] == 1
    assert monthly_taxes[10] == pytest.approx(1 + 0.1 * (16 / 30))
    assert monthly_taxes[11] == pytest.approx(1 + 0.1 * (10 / 31))
    assert fixed_charge is not None
    assert fixed_charge == pytest.approx((30 * (16 / 30) + 30 * (10 / 31)) / 12)


def test_build_energy_schedule_prorates_consumption_rows_by_season() -> None:
    season = Season(
        start=DayOfMonth(day=15, month=11),
        end=DayOfMonth(day=10, month=12),
    )
    baseline_row = ConsumptionRow(
        rate="Base",
        season=None,
        year=2025,
        effective_date=None,
        month_values=[1.0] * 12,
        location_avg_factor=1,
        rate_determinant="per therm",
    )
    seasonal_row = ConsumptionRow(
        rate="Winter Adder",
        season=season,
        year=2025,
        effective_date=None,
        month_values=[1.0] * 12,
        location_avg_factor=1,
        rate_determinant="per therm",
    )

    urdb = _build_energy_schedule_raw([baseline_row, seasonal_row], include_taxes=False)
    rate_structure = urdb.get("energyratestructure")
    schedules = urdb.get("energyweekdayschedule")
    assert rate_structure is not None
    assert schedules is not None

    october_rate = rate_structure[schedules[9][0]][0]["rate"]
    november_rate = rate_structure[schedules[10][0]][0]["rate"]
    december_rate = rate_structure[schedules[11][0]][0]["rate"]

    base_rate = round(1 / kwh_multiplier("per therm"), 6)
    assert october_rate == pytest.approx(base_rate)
    assert november_rate == pytest.approx(round((1 / kwh_multiplier("per therm")) * (1 + 16 / 30), 6))
    assert december_rate == pytest.approx(round((1 / kwh_multiplier("per therm")) * (1 + 10 / 31), 6))
