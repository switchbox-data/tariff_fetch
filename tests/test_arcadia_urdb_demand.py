from datetime import datetime
from math import inf
from types import SimpleNamespace
from typing import get_args

import pytest

from tariff_fetch.arcadia.schema.common import TariffChargeType
from tariff_fetch.urdb.arcadia.demandschedule import (
    get_rate_demand_bands_at_datetime,
    get_raw_bands_at_datetime,
)
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tests.arcadia_urdb_fixtures import make_band, make_property, make_rate, make_tariff

DEFAULT_QUANTITY_KEY = "SomeQuantityKey"
DEMAND_RATE_KW = {
    "quantity_key": DEFAULT_QUANTITY_KEY,
    "charge_type": "DEMAND_BASED",
}


def make_library_with_quantity_unit(quantity_unit: str = "kW") -> SimpleNamespace:
    class StubTariffLibrary:
        def get_property(self, key: str):
            assert key == DEFAULT_QUANTITY_KEY
            return make_property(key_name=key, quantity_unit=quantity_unit)

    return SimpleNamespace(tariffs=StubTariffLibrary(), variables=None)


def test_rate_demand_bands_at_datetime_simpliest_case():
    # rate = default_rate(rate_bands=[default_band(rate_amount=10.0)])
    library = make_library_with_quantity_unit()
    rate = make_rate(
        charge_type="DEMAND_BASED", quantity_key=DEFAULT_QUANTITY_KEY, rate_bands=[make_band(rate_amount=10.0)]
    )
    scenario = SimpleNamespace(apply_percentages=False)
    result = get_rate_demand_bands_at_datetime(
        rate,
        scenario,
        library,
        None,
    )
    expected = [(inf, 10.0)]
    assert result == expected


def test_rate_demand_bands_at_datetime_multiple_bands():
    library = make_library_with_quantity_unit()
    rate = make_rate(
        charge_type="DEMAND_BASED",
        quantity_key=DEFAULT_QUANTITY_KEY,
        rate_bands=[
            make_band(rate_amount=10.0, has_demand_limit=True, demand_upper_limit=250),
            make_band(rate_amount=20.0),
        ],
    )

    scenario = SimpleNamespace(apply_percentages=False)
    result = get_rate_demand_bands_at_datetime(
        rate,
        scenario,
        library,
        None,
    )
    expected = [(250.0, 10.0), (inf, 20)]
    assert result == expected


def test_rate_demand_bands_at_datetime_variable_rate_key():
    variable_rate_key = "TestVariableRateKey"
    dt_ = datetime(2025, 6, 1, 8, 30)
    variable_rate_value = 321.25

    class StubTariffLibrary:
        def get_property(self, key: str):
            assert key == DEFAULT_QUANTITY_KEY
            return make_property(key_name=key, quantity_unit="kW")

    class FakeVariableLibrary:
        def lookup(self, key: str, dt: datetime) -> float:
            assert key == variable_rate_key
            assert dt == dt_
            return variable_rate_value

    library = SimpleNamespace(tariffs=StubTariffLibrary(), variables=FakeVariableLibrary())
    band = make_band()
    rate = make_rate(
        quantity_key=DEFAULT_QUANTITY_KEY,
        variable_rate_key=variable_rate_key,
    )
    band = make_band(rate_amount=0.0)
    rate = make_rate(
        charge_type="DEMAND_BASED",
        quantity_key=DEFAULT_QUANTITY_KEY,
        variable_rate_key=variable_rate_key,
        rate_bands=[band],
    )
    scenario = SimpleNamespace(apply_percentages=False)
    result = get_rate_demand_bands_at_datetime(rate, scenario, library, dt_)
    expected = [(inf, variable_rate_value)]
    assert result == expected

    # If rate_amount is not 0, do not use variable rate
    band["rate_amount"] = 50.0
    result = get_rate_demand_bands_at_datetime(rate, scenario, library, dt_)
    expected = [(inf, 50.0)]
    assert result == expected


def test_rate_demand_bands_at_datetime_accepts_only_kw():
    library = make_library_with_quantity_unit("kVA")
    rate = make_rate(charge_type="DEMAND_BASED", quantity_key=DEFAULT_QUANTITY_KEY, rate_bands=[])
    match = "Unsupported demand quantity unit: kVA"
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)


def test_rate_demand_bands_at_datetime_must_have_bands():
    library = make_library_with_quantity_unit()
    rate = make_rate(charge_type="DEMAND_BASED", quantity_key=DEFAULT_QUANTITY_KEY, rate_bands=[])
    match = "Demand-based rates must have non-empty bands"
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)


@pytest.mark.parametrize("charge_type", [_ for _ in get_args(TariffChargeType) if _ != "DEMAND_BASED"])
def test_rate_demand_bands_must_be_demand_based(charge_type: TariffChargeType):
    rate = make_rate(charge_type=charge_type)
    _ = get_rate_demand_bands_at_datetime(rate, None, None, None)
    assert _ is None


def test_rate_demand_bands_must_not_have_consumption_limit():
    library = make_library_with_quantity_unit()
    band = make_band(consumption_upper_limit=10)
    rate = make_rate(charge_type="DEMAND_BASED", quantity_key=DEFAULT_QUANTITY_KEY, rate_bands=[band])
    match = "Demand bands with consumption limits are not supported"
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)
    del band["consumption_upper_limit"]
    band["has_consumption_limit"] = True
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)


def test_rate_demand_bands_must_not_have_property_limit():
    library = make_library_with_quantity_unit()
    band = make_band(property_upper_limit=10)
    rate = make_rate(charge_type="DEMAND_BASED", quantity_key=DEFAULT_QUANTITY_KEY, rate_bands=[band])
    match = "Bands with property limits are not supported"
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)

    del band["property_upper_limit"]
    band["has_property_limit"] = True
    with pytest.raises(RateConversionError, match=match):
        _ = get_rate_demand_bands_at_datetime(rate, None, library, None)


def test_get_raw_bands_at_datetime(monkeypatch: pytest.MonkeyPatch):
    dt_value = datetime(2025, 5, 1, 6, 30)
    rates = [
        make_rate(charge_type="CONSUMPTION_BASED"),
        make_rate(**DEMAND_RATE_KW, rate_bands=[make_band(rate_amount=5.0)]),
        make_rate(
            **DEMAND_RATE_KW,
            rate_bands=[make_band(rate_amount=7.0, demand_upper_limit=10), make_band(rate_amount=12.0)],
        ),
    ]
    scenario = SimpleNamespace(master_tariff_id=1)

    class StubTariffLibrary:
        def get_tariff_at_date(self, master_tariff_id: int, dt: datetime):
            assert dt.date() == dt_value.date()
            assert master_tariff_id == 1
            return make_tariff()

        def get_property(self, key: str):
            assert key == DEFAULT_QUANTITY_KEY
            return make_property(key_name=key, quantity_unit="kW")

    library = SimpleNamespace(tariffs=StubTariffLibrary(), variables=None)

    def tariff_iter_rates_for_dt(tariff, scenario, library, dt):
        assert dt == dt_value
        assert tariff["master_tariff_id"] == 1
        return rates

    monkeypatch.setattr(
        "tariff_fetch.urdb.arcadia.demandschedule.ru.tariff_iter_rates_for_dt", tariff_iter_rates_for_dt
    )
    result = get_raw_bands_at_datetime(scenario, library, dt_value)
    expected = [(10, 12), (inf, 17)]
    assert result == expected
