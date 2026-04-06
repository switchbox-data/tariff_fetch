from dataclasses import dataclass
from datetime import UTC, date, datetime, timezone
from math import inf
from types import SimpleNamespace
from typing import Any

from tariff_fetch.arcadia.schema.lookup import Lookup
from tariff_fetch.arcadia.schema.season import SeasonExtended
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyStandard
from tariff_fetch.arcadia.schema.tariffrate import TariffRateBand, TariffRateExtended


def make_band(**overrides: Any) -> TariffRateBand:
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
    return band  # pyright: ignore[reportReturnType]


def make_rate(**overrides: Any) -> TariffRateExtended:
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
    return rate  # pyright: ignore[reportReturnType]


def make_tariff(**overrides: Any) -> TariffExtended:
    tariff = {
        "is_active": True,
        "tariff_id": 1,
        "master_tariff_id": 1,
        "tariff_code": "R-1",
        "tariff_name": "Residential Service",
        "lse_id": 1,
        "lse_name": "Example Utility",
        "service_type": "ELECTRICITY",
        "tariff_type": "DEFAULT",
        "customer_class": "RESIDENTIAL",
        "territory_id": 1,
        "effective_date": date(2025, 1, 1),
        "end_date": None,
        "time_zone": "UTC",
        "billing_period": "MONTHLY",
        "currency": "USD",
        "charge_types": ["FIXED_PRICE"],
        "charge_period": "MONTHLY",
        "has_time_of_use_rates": False,
        "has_tiered_rates": False,
        "has_contracted_rates": False,
        "has_rate_applicability": False,
        "tariff_book_name": "Residential Service",
        "lse_code": "EXAMPLE",
        "closed_date": None,
        "min_monthly_consumption": None,
        "max_monthly_consumption": None,
        "min_monthly_demand": None,
        "max_monthly_demand": None,
        "has_tariff_applicability": False,
        "has_net_metering": False,
        "privacy": "PUBLIC",
        "properties": [],
        "rates": [],
    }
    tariff.update(overrides)
    return tariff  # pyright: ignore[reportReturnType]


def make_property(**overrides: Any) -> TariffPropertyStandard:
    tariff_property = {
        "key_name": "territoryId",
        "display_name": "Territory",
        "keyspace": "tariff",
        "family": "service",
        "description": "Example tariff property",
        "data_type": "CHOICE",
        "property_types": "APPLICABILITY",
        "operator": "=",
        "choices": [
            {
                "value": "1",
                "display_value": "Primary Territory",
                "data_value": "1",
            }
        ],
        "is_default": False,
    }
    tariff_property.update(overrides)
    return tariff_property  # pyright: ignore[reportReturnType]


def make_season(
    *, season_from_month: int, season_from_day: int, season_to_month: int, season_to_day: int, **overrides: Any
) -> SeasonExtended:
    result = {
        "season_id": 0,
        "lse_id": 0,
        "season_group_id": 0,
        "season_name": "season",
        "season_from_month": season_from_month,
        "season_from_day": season_from_day,
        "season_to_month": season_to_month,
        "season_to_day": season_to_day,
    }
    result.update(overrides)
    return result  # pyright: ignore[reportReturnType]


def make_fixed_rate(**overrides: Any) -> TariffRateExtended:
    return make_rate(**overrides)


def make_consumption_rate(**overrides: Any) -> TariffRateExtended:
    rate = make_rate(
        **{
            "charge_type": "CONSUMPTION_BASED",
            "rate_name": "Energy Charge",
            "rate_bands": [make_band(consumption_upper_limit=inf)],
            **overrides,
        }
    )
    return rate


def make_percentage_rate(**overrides: Any) -> TariffRateExtended:
    rate = make_rate(
        **{
            "charge_type": "FIXED_PRICE",
            "rate_name": "Percentage Charge",
            "rate_bands": [make_band(rate_unit="PERCENTAGE")],
            **overrides,
        }
    )
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


RATE = make_rate()
TARIFF = make_tariff()
PROPERTY = make_property()
BAND = make_band()
LOOKUP: Lookup = {
    "lookup_id": 0,
    "property_key": "TestKey",
    "from_date_time": datetime.fromtimestamp(0, tz=UTC),
    "to_date_time": datetime.max,
    "best_value": None,
    "actual_value": None,
    "forecast_value": None,
    "best_accuracy": None,
    "forecast_accuracy": None,
    "lse_forecast_accuracy": None,
    "lse_forecast_value": None,
}
