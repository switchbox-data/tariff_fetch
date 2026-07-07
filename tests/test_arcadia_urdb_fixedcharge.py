import pytest

from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.arcadia.fixedcharge import build_fixed_charge
from tariff_fetch.urdb.arcadia.library import Library, PropertyValue, TariffLibrary, VariablePropertyLibrary
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tests.arcadia_urdb_fixtures import BAND, PROPERTY, RATE, TARIFF


def make_stub_library(tariffs: list[TariffExtended], properties: dict[str, PropertyValue] | None = None) -> Library:
    tariff_library = TariffLibrary(None, None, tariffs)
    variables_library = VariablePropertyLibrary(None, None, None)
    return Library(None, properties, None, tariff_library=tariff_library, variables_library=variables_library)


def make_stub_scenario(tariff: TariffExtended) -> Scenario:
    return Scenario(tariff["master_tariff_id"], 2025, False)


def test_build_fixed_charge_inapplicable_bands_does_not_fail():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_type": "FIXED_PRICE",
                "applicability_key": "APPLICABLE",
                "charge_period": "MONTHLY",
                "rate_bands": [
                    {
                        **BAND,
                        "applicability_value": "true",
                        "rate_amount": 2.0,
                    }
                ],
                "quantity_key": "some_key",
            }
        ],
        "properties": [
            {
                "key_name": "APPLICABLE",
                "display_name": "applicable",
                "data_type": "BOOLEAN",
                "operator": "=",
                "keyspace": "tariff",
                "family": "service",
                "description": "applicability",
                "property_types": "APPLICABILITY",
                "is_default": False,
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff], properties={"APPLICABLE": "false"})
    result = build_fixed_charge(scenario, library)
    assert result.get("fixedchargefirstmeter") == 0


def test_build_fixed_charge_returns_zero_when_no_fixed_rates_apply():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_type": "CONSUMPTION_BASED",
                "rate_bands": [{**BAND, "rate_amount": 2.0, "calculation_factor": 1.0}],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    result = build_fixed_charge(scenario, library)

    assert result == {"fixedchargefirstmeter": 0, "fixedchargeunits": "$/month"}


def test_build_fixed_charge_converts_daily_to_monthly_average():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_period": "DAILY",
                "rate_bands": [{**BAND, "rate_amount": 2.0, "calculation_factor": 1.0}],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    result = build_fixed_charge(scenario, library)

    assert result.get("fixedchargefirstmeter") == pytest.approx(60.883, 0.001)
    assert result.get("fixedchargeunits") == "$/month"


def test_build_fixed_charge_applies_calculation_factor():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "rate_bands": [{**BAND, "rate_amount": 2.0, "calculation_factor": 1.5}],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    result = build_fixed_charge(scenario, library)

    assert result == {"fixedchargefirstmeter": 3.0, "fixedchargeunits": "$/month"}


def test_build_fixed_charge_rejects_unsupported_period():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_period": "ANNUALLY",
                "rate_bands": [{**BAND, "rate_amount": 1.0, "calculation_factor": 1.0}],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    with pytest.raises(RateConversionError, match="Fixed charges should be monthly or daily"):
        _ = build_fixed_charge(scenario, library)


def test_build_fixed_charge_rejects_quantity_key():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "quantity_key": "billingMeter",
                "rate_bands": [{**BAND, "calculation_factor": 1.0}],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    with pytest.raises(RateConversionError, match="quantity_key"):
        _ = build_fixed_charge(scenario, library)


def test_build_fixed_charge_rejects_variable_factors():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "variable_factor_key": "some_key",
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Fixed charges cannot have variable factors"
    with pytest.raises(RateConversionError, match=match):
        _ = build_fixed_charge(scenario, library)


def test_build_fixed_charge_with_billing_period_proration_factor():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_period": "MONTHLY",
                "variable_factor_key": "billingPeriodProrationFactor",
                "rate_bands": [
                    {**BAND, "rate_amount": 1000},
                ],
            }
        ],
    }
    # expected = mean([*([1000 * (31 / 30)] * 6), *([1000] * 5), 1000 * (28 / 30)])
    expected = (7 * 1000 * (31 / 30) + 4 * 1000 + 1000 * (28 / 30)) / 12
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_fixed_charge(scenario, library)
    assert result.get("fixedchargefirstmeter") == pytest.approx(expected, 0.001)


def test_build_fixed_charge_with_billing_period_proration_factor_monthly_only():
    tariff: TariffExtended = {
        **TARIFF,
        "rates": [
            {
                **RATE,
                "charge_period": "DAILY",
                "variable_factor_key": "billingPeriodProrationFactor",
                "rate_bands": [
                    {**BAND, "rate_amount": 1000},
                ],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Fixed charges cannot have variable factors"
    with pytest.raises(RateConversionError, match=match):
        _ = build_fixed_charge(scenario, library)
