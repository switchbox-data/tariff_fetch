from dataclasses import dataclass
from datetime import datetime
from math import inf
from types import SimpleNamespace

import pytest

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia import rateutils as ru
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.arcadia.scenario import Scenario


@dataclass
class _StubTariffLibrary:
    properties: dict[str, dict]  # pyright: ignore[reportMissingTypeArgument]

    def get_property(self, key: str):
        return self.properties[key]


class _StubLibrary:
    def __init__(
        self, *, properties: dict[str, object] | None = None, tariff_properties: dict[str, dict] | None = None
    ):
        self._properties = properties or {}
        self.tariffs = _StubTariffLibrary(tariff_properties or {})

    def get_property(self, key: str, data_type: str):
        return self._properties[key]

    def get_choice_property_as_ints(self, key: str) -> list[int]:
        values = self._properties[key]
        assert isinstance(values, list)
        return [int(value) for value in values]


def test_rate_filter_bands_excludes_non_matching_choice_band():
    rate = {
        "rate_bands": [
            {"applicability_value": "B", "rate_unit": "COST_PER_UNIT"},
        ],
        "applicability_key": "serviceVoltage",
    }
    library = _StubLibrary(
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
    band = {"applicability_value": "true", "rate_unit": "COST_PER_UNIT"}
    rate = {
        "rate_bands": [band],
        "applicability_key": "isSolar",
    }
    library = _StubLibrary(
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
        "rate_bands": [{"applicability_value": "A", "rate_unit": "COST_PER_UNIT"}],
        "applicability_key": "serviceVoltage",
    }
    library = _StubLibrary(
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


def test_rate_is_applied_to_scenario_filters_territory():
    rate = {
        "charge_class": ["SUPPLY"],
        "territory": {"territory_id": 2},
    }
    scenario = Scenario(1, 2025, False, {"SUPPLY"})
    library = _StubLibrary(properties={"territoryId": ["1"]})

    result = ru.rate_is_applied_to_scenario(rate, scenario, library)  # type: ignore[arg-type]

    assert result is False


def test_get_raw_bands_at_datetime_applies_matching_percentage(monkeypatch):
    consumption_rate = {
        "charge_type": "CONSUMPTION_BASED",
        "transaction_type": "BUY",
        "charge_class": ["SUPPLY"],
        "charge_period": "MONTHLY",
        "rate_bands": [
            {
                "tariff_rate_id": 1,
                "rate_unit": "COST_PER_UNIT",
                "rate_amount": 10.0,
                "is_credit": False,
                "consumption_upper_limit": inf,
            }
        ],
    }
    percentage_rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_class": ["SUPPLY"],
        "charge_period": "MONTHLY",
        "rate_bands": [
            {
                "tariff_rate_id": 2,
                "rate_unit": "PERCENTAGE",
                "rate_amount": 10.0,
                "is_credit": False,
            }
        ],
    }
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
    consumption_rate = {
        "charge_type": "CONSUMPTION_BASED",
        "transaction_type": "BUY",
        "charge_class": ["SUPPLY"],
        "charge_period": "MONTHLY",
        "rate_bands": [
            {
                "tariff_rate_id": 1,
                "rate_unit": "COST_PER_UNIT",
                "rate_amount": 10.0,
                "is_credit": False,
                "consumption_upper_limit": inf,
            }
        ],
    }
    percentage_rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_class": ["SUPPLY"],
        "charge_period": "MONTHLY",
        "rate_bands": [
            {
                "tariff_rate_id": 2,
                "rate_unit": "PERCENTAGE",
                "rate_amount": 10.0,
                "is_credit": False,
            }
        ],
    }
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
