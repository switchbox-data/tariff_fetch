from datetime import datetime
from math import inf

import pytest

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.arcadia.shared import is_weekday


def test_build_energy_schedule_keeps_weekday_and_weekend_distinct(monkeypatch):
    def fake_get_month_hour_bands(scenario, library, month, hour, day_filter):
        if day_filter is is_weekday:
            return [(inf, 1.0)]
        return [(inf, 2.0)]

    monkeypatch.setattr(es, "get_month_hour_bands", fake_get_month_hour_bands)

    result = es.build_energy_schedule(scenario=None, library=None)  # type: ignore[arg-type]

    assert result.get("energyratestructure") == [
        [{"rate": 1.0, "unit": "kWh"}],
        [{"rate": 2.0, "unit": "kWh"}],
    ]
    assert "energyweekdayschedule" in result
    assert "energyweekendschedule" in result
    assert result["energyweekdayschedule"][0][0] == 0
    assert result["energyweekendschedule"][0][0] == 1


def test_sum_piecewise_bands_aligns_and_collapses_values():
    result = es.sum_piecewise_bands(
        [
            [(100.0, 1.0), (inf, 2.0)],
            [(200.0, 0.5), (inf, 1.5)],
        ]
    )

    assert result == [(100.0, 1.5), (200.0, 2.5), (inf, 3.5)]


def test_average_aligned_bands_averages_inputs_and_collapses_duplicates():
    result = es.average_aligned_bands(
        [
            [(100.0, 1.0), (inf, 3.0)],
            [(100.0, 3.0), (inf, 3.0)],
        ]
    )

    assert result == [(100.0, 2.0), (inf, 3.0)]


def test_consumption_rate_rejects_unsupported_transaction_type():
    rate = {
        "charge_type": "CONSUMPTION_BASED",
        "transaction_type": "SELL_EXPORT",
        "charge_class": ["SUPPLY"],
        "charge_period": "MONTHLY",
        "rate_bands": [],
    }

    with pytest.raises(RateConversionError, match="Only BUY, BUY_IMPORT, and NET transactions are supported"):
        es.get_rate_consumption_bands_at_datetime(
            rate=rate,  # pyright: ignore[reportArgumentType]
            scenario=None,  # pyright: ignore[reportArgumentType]
            library=None,  # pyright: ignore[reportArgumentType]
            dt=datetime(2025, 1, 1, 0, 30),
        )


def test_percentage_rate_rejects_unsupported_transaction_type(monkeypatch):
    rate = {
        "transaction_type": "SELL_EXPORT",
        "charge_period": "MONTHLY",
        "charge_class": ["SUPPLY"],
        "rate_bands": [{"rate_unit": "PERCENTAGE"}],
    }

    monkeypatch.setattr(es.ru, "rate_get_band_units", lambda rate: {"PERCENTAGE"})

    with pytest.raises(RateConversionError, match="Only BUY, BUY_IMPORT, and NET transactions are supported"):
        es.get_percentage_rates_at_datetime(
            rates=[rate],  # pyright: ignore[reportArgumentType]
            scenario=None,  # pyright: ignore[reportArgumentType]
            library=None,  # pyright: ignore[reportArgumentType]
            dt=datetime(2025, 1, 1, 0, 30),
        )
