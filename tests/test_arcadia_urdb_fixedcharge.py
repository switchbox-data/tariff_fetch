from datetime import datetime

import pytest

from tariff_fetch.urdb.arcadia.fixedcharge import get_rate_fixed_charge_at_dt, normalize_fixed_charge_amount
from tests.arcadia_urdb_fixtures import make_band, make_fixed_rate


def test_get_rate_fixed_charge_returns_zero_when_no_bands_apply(monkeypatch):
    rate = make_fixed_rate(rate_bands=[])

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
    rate = make_fixed_rate(charge_period="DAILY", rate_bands=[make_band(rate_amount=2.0)])

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
