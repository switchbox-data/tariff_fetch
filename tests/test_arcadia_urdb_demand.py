from datetime import date

import pytest

from tariff_fetch.arcadia.schema.lookup import Lookup
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyStandard
from tariff_fetch.arcadia.schema.tariffrate import TariffRateBand, TariffRateExtended
from tariff_fetch.urdb.arcadia.demandschedule import (
    build_demand_schedule,
)
from tariff_fetch.urdb.arcadia.exception import RateConversionError
from tariff_fetch.urdb.arcadia.library import Library, PropertyTimeSeries, TariffLibrary, VariablePropertyLibrary
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tariff_fetch.urdb.schema import URDBRate
from tests.arcadia_urdb_fixtures import (
    BAND,
    LOOKUP,
    PROPERTY,
    RATE,
    TARIFF,
)

DEFAULT_QUANTITY_KEY = "SomeQuantityKey"
DEMAND_RATE: TariffRateExtended = {
    **RATE,
    "quantity_key": DEFAULT_QUANTITY_KEY,
    "charge_type": "DEMAND_BASED",
}

KW_PROPERTY: TariffPropertyStandard = {
    **PROPERTY,
    "quantity_key": DEFAULT_QUANTITY_KEY,
    "quantity_unit": "kW",
    "lookback_interval_quantity": 60,
}

KW_TARIFF: TariffExtended = {
    **TARIFF,
    "properties": [KW_PROPERTY],
}


def make_stub_library(tariffs: list[TariffExtended], property_timeseries: PropertyTimeSeries | None = None) -> Library:
    tariff_library = TariffLibrary(None, None, tariffs)
    variables_library = VariablePropertyLibrary(None, None, property_timeseries)
    return Library(None, None, None, tariff_library=tariff_library, variables_library=variables_library)


def make_stub_scenario(tariff: TariffExtended, apply_percentages: bool = False):
    return Scenario(tariff["master_tariff_id"], 2025, apply_percentages)


def schedule_lists_to_tuples(src: list[list[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(item) for item in src)


ZERO_SCHEDULES = schedule_lists_to_tuples([[0] * 24] * 12)


def assert_zero_schedules(result: URDBRate):
    schedule = ZERO_SCHEDULES
    assert result.get("demandweekdayschedule") == schedule
    assert result.get("demandweekendschedule") == schedule


def test_build_demand_schedule_simpliest_case():
    tariff: TariffExtended = {**KW_TARIFF, "rates": [{**DEMAND_RATE, "rate_bands": [{**BAND, "rate_amount": 10.0}]}]}
    tariffs = [tariff]
    scenario = make_stub_scenario(tariff)
    library = make_stub_library(tariffs)
    result = build_demand_schedule(scenario, library)
    assert result.get("demandratestructure") == [[{"rate": 10.0}]]
    assert_zero_schedules(result)


def test_build_demand_schedule_multiple_bands():
    tariff: TariffExtended = {
        **KW_TARIFF,
        "rates": [
            {
                **DEMAND_RATE,
                "rate_bands": [
                    {**BAND, "rate_amount": 10.0, "has_demand_limit": True, "demand_upper_limit": 250},
                    {**BAND, "rate_amount": 20.0},
                ],
            }
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_demand_schedule(scenario, library)
    expected = [[{"max": 250.0, "rate": 10.0}, {"rate": 20}]]
    assert result.get("demandratestructure") == expected
    assert_zero_schedules(result)


def test_build_schedule_variable_rate_key():
    key = LOOKUP["property_key"]
    lookup: Lookup = {**LOOKUP, "actual_value": 321.25}
    lookups: PropertyTimeSeries = {(key, 2025): [lookup]}
    tariff: TariffExtended = {
        **KW_TARIFF,
        "rates": [{**DEMAND_RATE, "variable_rate_key": key, "rate_bands": [{**BAND, "rate_amount": 0.0}]}],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff], lookups)
    result = build_demand_schedule(scenario, library)
    expected = [[{"rate": 321.25}]]
    assert result.get("demandratestructure") == expected
    assert_zero_schedules(result)


def test_build_schedule_variable_rate_key_ignore_if_nonzero():
    key = LOOKUP["property_key"]
    lookup: Lookup = {**LOOKUP, "actual_value": 321.25}
    lookups: PropertyTimeSeries = {(key, 2025): [lookup]}
    tariff: TariffExtended = {
        **KW_TARIFF,
        "rates": [{**DEMAND_RATE, "variable_rate_key": key, "rate_bands": [{**BAND, "rate_amount": 10.0}]}],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff], lookups)
    result = build_demand_schedule(scenario, library)
    expected = [[{"rate": 10.0}]]
    assert result.get("demandratestructure") == expected
    assert_zero_schedules(result)


def test_build_schedule_accepts_only_kw():
    tariff: TariffExtended = {
        **TARIFF,
        "properties": [{**PROPERTY, "quantity_key": DEFAULT_QUANTITY_KEY, "quantity_unit": "kVA"}],
        "rates": [{**DEMAND_RATE, "rate_bands": [{**BAND}]}],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Unsupported demand quantity unit: kVA"
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)


def test_build_schedule_rejects_variable_rate_key():
    tariff: TariffExtended = {**KW_TARIFF, "rates": [{**DEMAND_RATE, "variable_factor_key": "some_key"}]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Demand-based rates cannot have variable factors"
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)


def test_build_schedule_must_be_demand_based():
    tariff: TariffExtended = {
        **KW_TARIFF,
        "rates": [
            {**RATE, "rate_bands": [{**BAND, "rate_amount": 15.0}]},
            {**DEMAND_RATE, "rate_bands": [{**BAND, "rate_amount": 10.0}]},
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_demand_schedule(scenario, library)
    expected = [[{"rate": 10.0}]]
    assert result.get("demandratestructure") == expected
    assert_zero_schedules(result)


def test_build_schedule_rate_must_not_have_consumption_limit():
    band: TariffRateBand = {**BAND, "consumption_upper_limit": 10.0}
    tariff: TariffExtended = {**KW_TARIFF, "rates": [{**DEMAND_RATE, "rate_bands": [band]}]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Demand bands with consumption limits are not supported"
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)

    del band["consumption_upper_limit"]
    band["has_consumption_limit"] = True
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)


def test_build_schedule_rate_must_not_have_property_limit():
    band: TariffRateBand = {**BAND, "property_upper_limit": 10.0}
    tariff: TariffExtended = {**KW_TARIFF, "rates": [{**DEMAND_RATE, "rate_bands": [band]}]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    match = "Bands with property limits are not supported"
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)

    del band["property_upper_limit"]
    band["has_property_limit"] = True
    with pytest.raises(RateConversionError, match=match):
        _ = build_demand_schedule(scenario, library)


def test_build_demand_schedule_averages_sampled_datetimes():
    tariff: TariffExtended = {
        **TARIFF,
        "master_tariff_id": 1,
        "tariff_id": 2,
        "effective_date": date(2024, 6, 6),
        "end_date": date(2026, 6, 6),
        "properties": [
            {**KW_PROPERTY, "quantity_key": "base_kw", "quantity_unit": "kW"},
            {**KW_PROPERTY, "quantity_key": "seasonal_kw", "quantity_unit": "kW"},
        ],
        "rates": [
            {
                **RATE,
                "charge_type": "DEMAND_BASED",
                "quantity_key": "base_kw",
                "rate_bands": [{**BAND, "rate_amount": 5.0}],
            },
            {
                **RATE,
                "charge_type": "DEMAND_BASED",
                "quantity_key": "seasonal_kw",
                "rate_bands": [{**BAND, "rate_amount": 10.0}],
                "season": {
                    "season_id": 0,
                    "lse_id": 0,
                    "season_group_id": 0,
                    "season_name": "season",
                    "season_from_month": 5,
                    "season_from_day": 1,
                    "season_to_month": 5,
                    "season_to_day": 16,
                },
            },
        ],
    }
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])

    result = build_demand_schedule(scenario, library)

    base_schedule = [0] * 24
    may_weekday_schedule = [1] * 24
    may_weekend_schedule = [2] * 24

    assert result.get("demandratestructure") == [
        [{"rate": 5.0}],
        [{"rate": pytest.approx(10.454545)}],
        [{"rate": pytest.approx(9.444444)}],
    ]
    assert result.get("demandweekdayschedule") == schedule_lists_to_tuples(
        [base_schedule] * 4 + [may_weekday_schedule] + [base_schedule] * 7
    )
    assert result.get("demandweekendschedule") == schedule_lists_to_tuples(
        [base_schedule] * 4 + [may_weekend_schedule] + [base_schedule] * 7
    )


def test_build_demand_schedule_infers_demandwindow():
    tariff: TariffExtended = {**KW_TARIFF, "rates": [DEMAND_RATE]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_demand_schedule(scenario, library)
    assert result.get("demandwindow") == 60


def test_build_demand_schedule_returns_nothing_without_demand_rates():
    tariff: TariffExtended = {**TARIFF, "rates": [{**RATE, "charge_type": "CONSUMPTION_BASED", "rate_bands": [BAND]}]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_demand_schedule(scenario, library)
    assert "demandratestructure" not in result
    assert "demandweekdayschedule" not in result
    assert "demandweekendschedule" not in result


def test_build_demand_schedule_returns_demand_rate_unit():
    tariff: TariffExtended = {**KW_TARIFF, "rates": [DEMAND_RATE]}
    scenario = make_stub_scenario(tariff)
    library = make_stub_library([tariff])
    result = build_demand_schedule(scenario, library)
    assert result.get("demandrateunit") == "kW"
