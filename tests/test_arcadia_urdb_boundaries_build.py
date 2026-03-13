from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from tariff_fetch.urdb.arcadia import build as build_mod
from tariff_fetch.urdb.arcadia import metadata as metadata_mod
from tariff_fetch.urdb.arcadia import rateutils as ru
from tariff_fetch.urdb.arcadia.scenario import Scenario


def test_season_is_datetime_within_respects_start_inclusive_end_exclusive():
    season = {
        "season_from_month": 6,
        "season_from_day": 1,
        "season_to_month": 9,
        "season_to_day": 1,
    }

    assert ru.season_is_datetime_within(season, date(2025, 6, 1)) is True  # type: ignore[arg-type]
    assert ru.season_is_datetime_within(season, date(2025, 8, 31)) is True  # type: ignore[arg-type]
    assert ru.season_is_datetime_within(season, date(2025, 9, 1)) is False  # type: ignore[arg-type]


def test_season_is_datetime_within_handles_wraparound_year():
    season = {
        "season_from_month": 11,
        "season_from_day": 1,
        "season_to_month": 3,
        "season_to_day": 1,
    }

    assert ru.season_is_datetime_within(season, date(2025, 12, 15)) is True  # type: ignore[arg-type]
    assert ru.season_is_datetime_within(season, date(2025, 2, 15)) is True  # type: ignore[arg-type]
    assert ru.season_is_datetime_within(season, date(2025, 5, 1)) is False  # type: ignore[arg-type]


def test_period_is_datetime_within_respects_exclusive_to_portion():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 0,
        "from_hour": 0,
        "to_hour": 0,
        "from_minute": 0,
        "to_minute": 0,
    }
    # Monday 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 0, 0)) is True
    # Monday 12:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 12, 0)) is True
    # Monday 23:59
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 23, 59)) is True
    # Tuesday 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 0, 0)) is False
    # Tuesday 06:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 12, 0)) is False


def test_period_is_datetime_within_excludes_exact_to_boundary_for_non_wrapping_window():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 0,
        "from_hour": 14,
        "to_hour": 18,
        "from_minute": 0,
        "to_minute": 59,
    }

    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 18, 58)) is True
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 18, 59)) is False


def test_period_is_datetime_within_respects_day_isolation():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 2,
        "from_hour": 17,
        "to_hour": 8,
        "from_minute": 0,
        "to_minute": 0,
    }
    # Monday, 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 0, 0)) is True
    # Monday, 06:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 6, 0)) is True
    # Monday, 09:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 9, 0)) is False
    # Monday, 16:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 16, 0)) is False
    # Monday, 17:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 17, 0)) is True
    # Monday, 23:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 23, 0)) is True
    # Tuesday, 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 0, 0)) is True
    # Tuesday, 06:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 6, 0)) is True
    # Tuesday, 09:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 9, 0)) is False
    # Tuesday, 16:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 16, 0)) is False
    # Tuesday, 17:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 17, 0)) is True
    # Tuesday, 23:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 3, 23, 0)) is True
    # Wednesday, 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 0, 0)) is True
    # Wednesday, 06:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 6, 0)) is True
    # Wednesday, 09:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 9, 0)) is False
    # Wednesday, 16:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 16, 0)) is False
    # Wednesday, 17:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 17, 0)) is True
    # Wednesday, 23:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 23, 0)) is True
    # Thursday, 00:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 0, 0)) is False
    # Thursday, 06:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 6, 0)) is False
    # Thursday, 09:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 9, 0)) is False
    # Thursday, 16:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 16, 0)) is False
    # Thursday, 17:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 17, 0)) is False
    # Thursday, 23:00
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 5, 23, 0)) is False


def test_period_is_datetime_within_excludes_exact_to_boundary_for_wrapping_window():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 2,
        "from_hour": 17,
        "to_hour": 8,
        "from_minute": 0,
        "to_minute": 0,
    }

    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 7, 59)) is True
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 2, 8, 0)) is False
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 7, 59)) is True
    assert ru.period_is_datetime_within(period, datetime(2025, 6, 4, 8, 0)) is False


def test_time_of_use_is_datetime_within_applies_embedded_season():
    tou = {
        "season": {
            "season_from_month": 6,
            "season_from_day": 1,
            "season_to_month": 9,
            "season_to_day": 1,
        },
        "tou_periods": [
            {
                "from_day_of_week": 0,
                "to_day_of_week": 6,
                "from_hour": 14,
                "to_hour": 18,
                "from_minute": 0,
                "to_minute": 59,
            }
        ],
    }

    assert ru.time_of_use_is_datetime_within(tou, datetime(2025, 7, 10, 15, 30)) is True  # type: ignore[arg-type]
    assert ru.time_of_use_is_datetime_within(tou, datetime(2025, 10, 10, 15, 30)) is False  # type: ignore[arg-type]
    assert ru.time_of_use_is_datetime_within(tou, datetime(2025, 7, 10, 12, 30)) is False  # type: ignore[arg-type]


def test_rate_is_applied_to_datetime_respects_rate_level_effective_window():
    rate = {
        "from_date_time": datetime(2025, 3, 1, 0, 0),
        "to_date_time": datetime(2025, 6, 1, 0, 0),
    }

    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 2, 28, 23, 59)) is False  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 3, 1, 0, 0)) is True  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 5, 31, 23, 59)) is True  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 6, 1, 0, 0)) is False  # type: ignore[arg-type]


def test_rate_is_applied_to_datetime_combines_effective_window_with_season_and_tou():
    rate = {
        "from_date_time": datetime(2025, 6, 1, 0, 0),
        "to_date_time": datetime(2025, 9, 1, 0, 0),
        "season": {
            "season_from_month": 6,
            "season_from_day": 1,
            "season_to_month": 9,
            "season_to_day": 1,
        },
        "time_of_use": {
            "tou_periods": [
                {
                    "from_day_of_week": 0,
                    "to_day_of_week": 6,
                    "from_hour": 14,
                    "to_hour": 18,
                    "from_minute": 0,
                    "to_minute": 59,
                }
            ]
        },
    }

    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 7, 10, 15, 30)) is True  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 5, 31, 15, 30)) is False  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 7, 10, 12, 30)) is False  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 9, 1, 0, 0)) is False  # type: ignore[arg-type]


def test_rate_is_applied_to_datetime_handles_offset_aware_rate_window():
    rate = {
        "from_date_time": datetime(2025, 3, 1, 0, 0, tzinfo=timezone.utc),
        "to_date_time": datetime(2025, 6, 1, 0, 0, tzinfo=timezone.utc),
    }

    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 2, 28, 23, 59)) is False  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 3, 1, 0, 0)) is True  # type: ignore[arg-type]
    assert ru.rate_is_applied_to_datetime(rate, datetime(2025, 6, 1, 0, 0)) is False  # type: ignore[arg-type]


def test_time_of_use_is_datetime_within_ignores_calendar_id():
    tou = {
        "calendar_id": 10,
        "tou_periods": [
            {
                "from_day_of_week": 0,
                "to_day_of_week": 6,
                "from_hour": 0,
                "to_hour": 23,
                "from_minute": 0,
                "to_minute": 59,
            }
        ],
    }

    assert ru.time_of_use_is_datetime_within(tou, datetime(2025, 7, 10, 15, 30)) is True  # type: ignore[arg-type]


def test_period_is_datetime_within_ignores_calendar_id():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 6,
        "from_hour": 0,
        "to_hour": 23,
        "from_minute": 0,
        "to_minute": 59,
        "calendar_id": 10,
    }

    assert ru.period_is_datetime_within(period, datetime(2025, 7, 10, 15, 30)) is True  # type: ignore[arg-type]


def test_tariff_iter_rates_for_dt_records_ignored_calendar_issues_once():
    rate = {
        "tariff_rate_id": 10,
        "rate_name": "TOU Charge",
        "charge_class": ["SUPPLY"],
        "rate_bands": [{"rate_unit": "COST_PER_UNIT"}],
        "time_of_use": {
            "calendar_id": 10,
            "tou_periods": [
                {
                    "tou_period_id": 33,
                    "from_day_of_week": 0,
                    "to_day_of_week": 6,
                    "from_hour": 0,
                    "to_hour": 23,
                    "from_minute": 0,
                    "to_minute": 59,
                    "calendar_id": 11,
                }
            ],
        },
    }
    messages: list[tuple[tuple[object, ...], str]] = []
    library = SimpleNamespace(
        record_issue=lambda key, message: messages.append((key, message)),
        get_choice_property_as_ints=lambda key: [1],
    )
    tariff = {"rates": [rate]}
    scenario = Scenario(1, 2025, False, {"SUPPLY"})

    _ = list(
        ru.tariff_iter_rates_for_dt(
            tariff,  # type: ignore[arg-type]
            scenario,
            library,  # type: ignore[arg-type]
            datetime(2025, 7, 10, 15, 30),
        )
    )

    assert messages == [
        (
            ("ignored_tou_calendar", 10, 10),
            "Ignoring TOU calendar_id 10 for rate 10 (TOU Charge)",
        ),
        (
            ("ignored_tou_period_calendar", 10, 33, 11),
            "Ignoring TOU period calendar_id 11 for rate 10 (TOU Charge)",
        ),
    ]


def test_build_urdb_merges_converter_chunks(monkeypatch):
    scenario = Scenario(123, 2025, apply_percentages=True, charge_classes={"SUPPLY"})

    monkeypatch.setattr(build_mod, "Library", lambda api: SimpleNamespace())
    monkeypatch.setattr(
        build_mod,
        "build_energy_schedule",
        lambda scenario, library: {"energyratestructure": [[{"rate": 1.0, "unit": "kWh"}]]},
    )
    monkeypatch.setattr(
        build_mod,
        "build_fixed_charge",
        lambda scenario, library: {"fixedchargefirstmeter": 12.0, "fixedchargeunits": "$/month"},
    )
    monkeypatch.setattr(
        build_mod,
        "build_metadata",
        lambda scenario, library: {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"},
    )

    result = build_mod.build_urdb(api=object(), scenario=scenario)  # type: ignore[arg-type]

    assert result == {
        "energyratestructure": [[{"rate": 1.0, "unit": "kWh"}]],
        "fixedchargefirstmeter": 12.0,
        "fixedchargeunits": "$/month",
        "label": "UTIL",
        "utility": "Utility",
        "name": "Tariff",
        "country": "USA",
    }


def test_build_metadata_reads_tariff_for_start_of_year():
    captured: list[tuple[int, date]] = []

    def get_tariff_at_date(master_tariff_id: int, dt: date):
        captured.append((master_tariff_id, dt))
        return {
            "lse_code": "UTIL",
            "lse_name": "Utility Name",
            "tariff_name": "Residential Service",
        }

    library = SimpleNamespace(tariffs=SimpleNamespace(get_tariff_at_date=get_tariff_at_date))

    result = metadata_mod.build_metadata(Scenario(456, 2025, apply_percentages=False), library)  # type: ignore[arg-type]

    assert captured == [(456, date(2025, 1, 1))]
    assert result == {
        "label": "UTIL",
        "utility": "Utility Name",
        "name": "Residential Service",
        "country": "USA",
    }
