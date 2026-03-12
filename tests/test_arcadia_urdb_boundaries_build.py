from datetime import date, datetime
from types import SimpleNamespace

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


def test_period_is_datetime_within_respects_inclusive_boundaries():
    period = {
        "from_day_of_week": 0,
        "to_day_of_week": 4,
        "from_hour": 9,
        "to_hour": 17,
        "from_minute": 0,
        "to_minute": 59,
    }

    assert ru.period_is_datetime_within(period, datetime(2025, 1, 6, 9, 0)) is True  # type: ignore[arg-type]
    assert ru.period_is_datetime_within(period, datetime(2025, 1, 10, 17, 59)) is True  # type: ignore[arg-type]
    assert ru.period_is_datetime_within(period, datetime(2025, 1, 11, 12, 0)) is False  # type: ignore[arg-type]
    assert ru.period_is_datetime_within(period, datetime(2025, 1, 6, 8, 59)) is False  # type: ignore[arg-type]


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


def test_build_urdb_merges_converter_chunks(monkeypatch):
    scenario = Scenario(123, 2025, apply_percentages=True, charge_classes={"SUPPLY"})

    monkeypatch.setattr(build_mod, "Library", lambda api: SimpleNamespace())
    monkeypatch.setattr(build_mod, "build_energy_schedule", lambda scenario, library: {"energyratestructure": [[{"rate": 1.0, "unit": "kWh"}]]})
    monkeypatch.setattr(build_mod, "build_fixed_charge", lambda scenario, library: {"fixedchargefirstmeter": 12.0, "fixedchargeunits": "$/month"})
    monkeypatch.setattr(build_mod, "build_metadata", lambda scenario, library: {"label": "UTIL", "utility": "Utility", "name": "Tariff", "country": "USA"})

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
