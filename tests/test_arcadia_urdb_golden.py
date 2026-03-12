from datetime import datetime
from math import inf
from types import SimpleNamespace

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia import fixedcharge as fc
from tariff_fetch.urdb.arcadia import metadata as metadata_mod
from tariff_fetch.urdb.arcadia.scenario import Scenario


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
    tariff = {"rates": []}
    fixed_rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_period": "MONTHLY",
        "tariff_rate_id": 1,
        "rate_name": "Customer Charge",
        "rate_bands": [
            {
                "tariff_rate_id": 1,
                "rate_unit": "COST_PER_UNIT",
                "rate_amount": 12.5,
                "is_credit": False,
                "has_consumption_limit": False,
                "has_demand_limit": False,
                "has_property_limit": False,
            }
        ],
    }
    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff_at_date=lambda master_tariff_id, dt: tariff, get_rate=lambda rate_id: fixed_rate),
        variables=None,
    )

    monkeypatch.setattr(fc.ru, "tariff_iter_rates_for_dt", lambda tariff, scenario, library, dt: [fixed_rate])
    monkeypatch.setattr(fc.ru, "rate_filter_bands", lambda rate, scenario, library: list(rate["rate_bands"]))
    monkeypatch.setattr(fc.ru, "rate_band_get_amount_at_datetime", lambda band, library, dt: band["rate_amount"])

    result = fc.build_fixed_charge(Scenario(1, 2025, apply_percentages=False), library)  # type: ignore[arg-type]

    assert result == {
        "fixedchargefirstmeter": 12.5,
        "fixedchargeunits": "$/month",
    }


def test_golden_daily_fixed_charge_build(monkeypatch):
    tariff = {"rates": []}
    fixed_rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_period": "DAILY",
        "tariff_rate_id": 1,
        "rate_name": "Customer Charge",
        "rate_bands": [
            {
                "tariff_rate_id": 1,
                "rate_unit": "COST_PER_UNIT",
                "rate_amount": 1.0,
                "is_credit": False,
                "has_consumption_limit": False,
                "has_demand_limit": False,
                "has_property_limit": False,
            }
        ],
    }
    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff_at_date=lambda master_tariff_id, dt: tariff, get_rate=lambda rate_id: fixed_rate),
        variables=None,
    )

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
