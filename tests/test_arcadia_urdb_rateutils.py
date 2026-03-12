from datetime import datetime
from math import inf
from types import SimpleNamespace

import pytest

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia import rateutils as ru
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tests.arcadia_urdb_fixtures import StubLibrary, make_band, make_consumption_rate, make_percentage_rate


def test_rate_filter_bands_excludes_non_matching_choice_band():
    rate = {
        "rate_bands": [make_band(applicability_value="B")],
        "applicability_key": "serviceVoltage",
    }
    library = StubLibrary(
        properties={"serviceVoltage": ["A"]},
        tariff_properties={
            "serviceVoltage": {
                "key_name": "serviceVoltage",
                "property_types": "APPLICABILITY",
                "operator": "=",
                "data_type": "CHOICE",
            }
        },
    )

    result = ru.rate_filter_bands(rate, Scenario(1, 2025, False), library)  # type: ignore[arg-type]

    assert result == []


def test_rate_filter_bands_includes_matching_boolean_band():
    band = make_band(applicability_value="true")
    rate = {
        "rate_bands": [band],
        "applicability_key": "isSolar",
    }
    library = StubLibrary(
        properties={"isSolar": True},
        tariff_properties={
            "isSolar": {
                "key_name": "isSolar",
                "property_types": "RATE_CRITERIA",
                "operator": "=",
                "data_type": "BOOLEAN",
            }
        },
    )

    result = ru.rate_filter_bands(rate, Scenario(1, 2025, False), library)  # type: ignore[arg-type]

    assert result == [band]


def test_rate_filter_bands_rejects_unsupported_operator():
    rate = {
        "rate_bands": [make_band(applicability_value="A")],
        "applicability_key": "serviceVoltage",
    }
    library = StubLibrary(
        properties={"serviceVoltage": ["A"]},
        tariff_properties={
            "serviceVoltage": {
                "key_name": "serviceVoltage",
                "property_types": "APPLICABILITY",
                "operator": "!=",
                "data_type": "CHOICE",
            }
        },
    )

    with pytest.raises(RateConversionError, match="Only `=` operators are supported"):
        ru.rate_filter_bands(rate, Scenario(1, 2025, False), library)  # type: ignore[arg-type]


def test_rate_filter_bands_rejects_variable_limit_key():
    rate = {
        "variable_limit_key": "demandMultiplierTiers",
        "rate_bands": [make_band()],
    }

    with pytest.raises(RateConversionError, match="variable_limit_key"):
        ru.rate_filter_bands(rate, Scenario(1, 2025, False), StubLibrary())  # type: ignore[arg-type]


def test_rate_is_applied_to_scenario_filters_territory():
    rate = {
        "charge_class": ["SUPPLY"],
        "territory": {"territory_id": 2},
    }
    scenario = Scenario(1, 2025, False, {"SUPPLY"})
    library = StubLibrary(properties={"territoryId": ["1"]})

    result = ru.rate_is_applied_to_scenario(rate, scenario, library)  # type: ignore[arg-type]

    assert result is False


def test_get_raw_bands_at_datetime_applies_matching_percentage(monkeypatch):
    consumption_rate = make_consumption_rate(rate_bands=[make_band(rate_amount=10.0, consumption_upper_limit=inf)])
    percentage_rate = make_percentage_rate(
        rate_bands=[make_band(tariff_rate_id=2, rate_unit="PERCENTAGE", rate_amount=10.0)]
    )
    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff_at_date=lambda master_tariff_id, dt: {"rates": []}),
        variables=None,
    )

    monkeypatch.setattr(
        es.ru, "tariff_iter_rates_for_dt", lambda tariff, scenario, library, dt: [consumption_rate, percentage_rate]
    )
    monkeypatch.setattr(es.ru, "rate_filter_bands", lambda rate, scenario, library: list(rate["rate_bands"]))
    monkeypatch.setattr(es.ru, "rate_band_get_amount_at_datetime", lambda band, library, dt: band["rate_amount"])

    result = es.get_raw_bands_at_datetime(
        Scenario(1, 2025, apply_percentages=True, charge_classes={"SUPPLY"}),
        library,  # pyright: ignore[reportArgumentType]
        datetime(2025, 1, 1, 0, 30),
    )

    assert result == [(inf, 11.0)]


def test_get_raw_bands_at_datetime_skips_percentage_when_disabled(monkeypatch):
    consumption_rate = make_consumption_rate(rate_bands=[make_band(rate_amount=10.0, consumption_upper_limit=inf)])
    percentage_rate = make_percentage_rate(
        rate_bands=[make_band(tariff_rate_id=2, rate_unit="PERCENTAGE", rate_amount=10.0)]
    )
    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff_at_date=lambda master_tariff_id, dt: {"rates": []}),
        variables=None,
    )

    monkeypatch.setattr(
        es.ru, "tariff_iter_rates_for_dt", lambda tariff, scenario, library, dt: [consumption_rate, percentage_rate]
    )
    monkeypatch.setattr(es.ru, "rate_filter_bands", lambda rate, scenario, library: list(rate["rate_bands"]))
    monkeypatch.setattr(es.ru, "rate_band_get_amount_at_datetime", lambda band, library, dt: band["rate_amount"])

    result = es.get_raw_bands_at_datetime(
        Scenario(1, 2025, apply_percentages=False, charge_classes={"SUPPLY"}),
        library,  # pyright: ignore[reportArgumentType]
        datetime(2025, 1, 1, 0, 30),
    )

    assert result == [(inf, 10.0)]


def test_rate_band_get_amount_at_datetime_rejects_variable_factor_key():
    band = make_band(tariff_rate_id=7, rate_amount=5.0)
    rate = make_consumption_rate(tariff_rate_id=7, variable_factor_key="billingPeriodProrationFactor")
    library = SimpleNamespace(tariffs=SimpleNamespace(get_rate=lambda rate_id: rate))

    with pytest.raises(RateConversionError, match="variable_factor_key"):
        ru.rate_band_get_amount_at_datetime(
            band,  # type: ignore[arg-type]
            library,  # type: ignore[arg-type]
            datetime(2025, 1, 1, 0, 30),
        )


def test_get_rate_consumption_bands_rejects_quantity_key():
    rate = make_consumption_rate(quantity_key="billingMeter")

    with pytest.raises(RateConversionError, match="quantity_key"):
        es.get_rate_consumption_bands_at_datetime(
            rate=rate,  # type: ignore[arg-type]
            scenario=None,  # pyright: ignore[reportArgumentType]
            library=None,  # pyright: ignore[reportArgumentType]
            dt=datetime(2025, 1, 1, 0, 30),
        )
