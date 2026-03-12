from datetime import datetime

import pytest

from tariff_fetch.urdb.arcadia.fixedcharge import get_rate_fixed_charge_at_dt, normalize_fixed_charge_amount


def test_get_rate_fixed_charge_returns_zero_when_no_bands_apply(monkeypatch):
    rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_period": "MONTHLY",
        "tariff_rate_id": 1,
        "rate_name": "Customer Charge",
    }

    monkeypatch.setattr(
        "tariff_fetch.urdb.arcadia.fixedcharge.ru.rate_filter_bands",
        lambda rate, scenario, library: [],
    )

    result = get_rate_fixed_charge_at_dt(
        scenario=None,  # pyright: ignore[reportArgumentType]
        library=None,  # pyright: ignore[reportArgumentType]
        rate=rate,  # pyright: ignore[reportArgumentType]
        dt=datetime(2025, 1, 1, 0, 30),
    )

    assert result == 0


def test_get_rate_fixed_charge_converts_daily_to_monthly(monkeypatch):
    rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_period": "DAILY",
        "tariff_rate_id": 1,
        "rate_name": "Customer Charge",
        "rate_bands": [
            {
                "rate_unit": "COST_PER_UNIT",
                "rate_amount": 2.0,
                "has_consumption_limit": False,
                "has_demand_limit": False,
                "has_property_limit": False,
            }
        ],
    }

    monkeypatch.setattr(
        "tariff_fetch.urdb.arcadia.fixedcharge.ru.rate_filter_bands",
        lambda rate, scenario, library: list(rate["rate_bands"]),
    )
    monkeypatch.setattr(
        "tariff_fetch.urdb.arcadia.fixedcharge.ru.rate_band_get_amount_at_datetime",
        lambda band, library, dt: band["rate_amount"],
    )

    result = get_rate_fixed_charge_at_dt(
        scenario=None,  # pyright: ignore[reportArgumentType]
        library=None,  # pyright: ignore[reportArgumentType]
        rate=rate,  # pyright: ignore[reportArgumentType]
        dt=datetime(2025, 2, 1, 0, 30),
    )

    assert result == 56.0


def test_normalize_fixed_charge_amount_rejects_unsupported_period():
    with pytest.raises(ValueError, match="Unsupported fixed charge period"):
        normalize_fixed_charge_amount(1.0, "YEARLY", datetime(2025, 1, 1, 0, 30))
