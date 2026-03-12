from datetime import datetime

from tariff_fetch.urdb.arcadia.fixedcharge import get_rate_fixed_charge_at_dt


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
