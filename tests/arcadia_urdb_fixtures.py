from dataclasses import dataclass
from math import inf
from types import SimpleNamespace
from typing import Any


def make_band(**overrides: Any) -> dict[str, Any]:
    band = {
        "tariff_rate_id": 1,
        "rate_unit": "COST_PER_UNIT",
        "rate_amount": 1.0,
        "is_credit": False,
        "has_consumption_limit": False,
        "consumption_upper_limit": None,
        "has_demand_limit": False,
        "demand_upper_limit": None,
        "has_property_limit": False,
        "property_upper_limit": None,
        "calculation_factor": None,
        "applicability_formula": None,
    }
    band.update(overrides)
    return band


def make_rate(**overrides: Any) -> dict[str, Any]:
    rate = {
        "charge_type": "FIXED_PRICE",
        "transaction_type": "BUY",
        "charge_period": "MONTHLY",
        "charge_class": ["SUPPLY"],
        "tariff_rate_id": 1,
        "rate_name": "Customer Charge",
        "rate_bands": [make_band()],
    }
    rate.update(overrides)
    return rate


def make_fixed_rate(**overrides: Any) -> dict[str, Any]:
    return make_rate(**overrides)


def make_consumption_rate(**overrides: Any) -> dict[str, Any]:
    rate = make_rate(
        charge_type="CONSUMPTION_BASED",
        rate_name="Energy Charge",
        rate_bands=[make_band(consumption_upper_limit=inf)],
    )
    rate.update(overrides)
    return rate


def make_percentage_rate(**overrides: Any) -> dict[str, Any]:
    rate = make_rate(
        charge_type="FIXED_PRICE",
        rate_name="Percentage Charge",
        rate_bands=[make_band(rate_unit="PERCENTAGE")],
    )
    rate.update(overrides)
    return rate


def make_library_with_tariff(rate: dict[str, Any]) -> SimpleNamespace:
    tariff = {"rates": []}
    return SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff_at_date=lambda master_tariff_id, dt: tariff, get_rate=lambda rate_id: rate),
        variables=None,
    )


@dataclass
class StubTariffLibrary:
    properties: dict[str, dict[str, object]]

    def get_property(self, key: str) -> dict[str, object]:
        return self.properties[key]


class StubLibrary:
    def __init__(
        self,
        *,
        properties: dict[str, object] | None = None,
        tariff_properties: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self._properties = properties or {}
        self.tariffs = StubTariffLibrary(tariff_properties or {})

    def get_property(self, key: str, data_type: str) -> object:
        return self._properties[key]

    def get_choice_property_as_ints(self, key: str) -> list[int]:
        values = self._properties[key]
        assert isinstance(values, list)
        return [int(value) for value in values]
