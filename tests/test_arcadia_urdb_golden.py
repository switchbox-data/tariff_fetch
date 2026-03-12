from datetime import datetime
from math import inf
from types import SimpleNamespace

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia import fixedcharge as fc
from tariff_fetch.urdb.arcadia import metadata as metadata_mod
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tests.arcadia_urdb_fixtures import make_band, make_fixed_rate, make_library_with_tariff


def test_golden_flat_energy_schedule(monkeypatch):
    monkeypatch.setattr(es, "get_month_hour_bands", lambda scenario, library, month, hour, day_filter: [(inf, 0.15)])

    result = es.build_energy_schedule(Scenario(1, 2025, apply_percentages=False), library=None)  # type: ignore[arg-type]

    assert result == {
        "energyratestructure": [[{"rate": 0.15, "unit": "kWh"}]],
        "energyweekdayschedule": tuple(tuple(0 for _ in range(24)) for _ in range(12)),
        "energyweekendschedule": tuple(tuple(0 for _ in range(24)) for _ in range(12)),
    }


def test_golden_tiered_energy_schedule(monkeypatch):
    monkeypatch.setattr(
        es,
        "get_month_hour_bands",
        lambda scenario, library, month, hour, day_filter: [(100.0, 0.1), (inf, 0.2)],
    )

    result = es.build_energy_schedule(Scenario(1, 2025, apply_percentages=False), library=None)  # type: ignore[arg-type]

    assert result == {
        "energyratestructure": [[{"rate": 0.1, "max": 100.0, "unit": "kWh"}, {"rate": 0.2, "unit": "kWh"}]],
        "energyweekdayschedule": tuple(tuple(0 for _ in range(24)) for _ in range(12)),
        "energyweekendschedule": tuple(tuple(0 for _ in range(24)) for _ in range(12)),
    }


def test_golden_fixed_charge_build(monkeypatch):
    fixed_rate = make_fixed_rate(rate_bands=[make_band(rate_amount=12.5)])
    library = make_library_with_tariff(fixed_rate)

    monkeypatch.setattr(fc.ru, "tariff_iter_rates_for_dt", lambda tariff, scenario, library, dt: [fixed_rate])
    monkeypatch.setattr(fc.ru, "rate_filter_bands", lambda rate, scenario, library: list(rate["rate_bands"]))
    monkeypatch.setattr(fc.ru, "rate_band_get_amount_at_datetime", lambda band, library, dt: band["rate_amount"])

    result = fc.build_fixed_charge(Scenario(1, 2025, apply_percentages=False), library)  # type: ignore[arg-type]

    assert result == {
        "fixedchargefirstmeter": 12.5,
        "fixedchargeunits": "$/month",
    }


def test_golden_daily_fixed_charge_build(monkeypatch):
    fixed_rate = make_fixed_rate(charge_period="DAILY", rate_bands=[make_band(rate_amount=1.0)])
    library = make_library_with_tariff(fixed_rate)

    monkeypatch.setattr(fc.ru, "tariff_iter_rates_for_dt", lambda tariff, scenario, library, dt: [fixed_rate])
    monkeypatch.setattr(fc.ru, "rate_filter_bands", lambda rate, scenario, library: list(rate["rate_bands"]))
    monkeypatch.setattr(fc.ru, "rate_band_get_amount_at_datetime", lambda band, library, dt: band["rate_amount"])

    result = fc.get_fixed_charge_at_dt(
        Scenario(1, 2025, apply_percentages=False),
        library,  # type: ignore[arg-type]
        datetime(2025, 4, 1, 0, 30),
    )

    assert result == 30.0


def test_golden_metadata_chunk():
    library = SimpleNamespace(
        tariffs=SimpleNamespace(
            get_tariff_at_date=lambda master_tariff_id, dt: {
                "lse_code": "CONED",
                "lse_name": "Consolidated Edison",
                "tariff_name": "Service Classification 1",
            }
        )
    )

    result = metadata_mod.build_metadata(Scenario(2252, 2025, apply_percentages=False), library)  # type: ignore[arg-type]

    assert result == {
        "label": "CONED",
        "utility": "Consolidated Edison",
        "name": "Service Classification 1",
        "country": "USA",
    }
