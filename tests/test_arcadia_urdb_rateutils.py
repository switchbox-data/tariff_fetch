from datetime import datetime
from math import inf
from types import SimpleNamespace

import pytest
from requests import HTTPError, Response

from tariff_fetch.urdb.arcadia import energyschedule as es
from tariff_fetch.urdb.arcadia import rateutils as ru
from tariff_fetch.urdb.arcadia.exception import RateConversionError, TariffAccessDenied
from tariff_fetch.urdb.arcadia.library import LibraryDebugStore, TariffLibrary
from tariff_fetch.urdb.arcadia.scenario import Scenario
from tests.arcadia_urdb_fixtures import StubLibrary, make_band, make_consumption_rate, make_percentage_rate, make_rate


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


def test_rate_band_get_amount_at_datetime_rejects_variable_rate_sub_key():
    band = make_band(tariff_rate_id=8, rate_amount=5.0)
    rate = make_consumption_rate(tariff_rate_id=8, variable_rate_sub_key="zoneA")
    library = SimpleNamespace(tariffs=SimpleNamespace(get_rate=lambda rate_id: rate))

    with pytest.raises(RateConversionError, match="variable_rate_sub_key"):
        ru.rate_band_get_amount_at_datetime(
            band,  # type: ignore[arg-type]
            library,  # type: ignore[arg-type]
            datetime(2025, 1, 1, 0, 30),
        )


def test_rate_band_get_amount_at_datetime_applies_calculation_factor_to_fixed_amount():
    band = make_band(tariff_rate_id=10, rate_amount=5.0, calculation_factor=1.5)
    rate = make_consumption_rate(tariff_rate_id=10)
    library = SimpleNamespace(tariffs=SimpleNamespace(get_rate=lambda rate_id: rate))

    result = ru.rate_band_get_amount_at_datetime(
        band,  # type: ignore[arg-type]
        library,  # type: ignore[arg-type]
        datetime(2025, 1, 1, 0, 30),
    )

    assert result == 7.5


def test_rate_band_get_amount_at_datetime_applies_calculation_factor_to_credit_band():
    band = make_band(tariff_rate_id=11, rate_amount=5.0, calculation_factor=1.5, is_credit=True)
    rate = make_consumption_rate(tariff_rate_id=11)
    library = SimpleNamespace(tariffs=SimpleNamespace(get_rate=lambda rate_id: rate))

    result = ru.rate_band_get_amount_at_datetime(
        band,  # type: ignore[arg-type]
        library,  # type: ignore[arg-type]
        datetime(2025, 1, 1, 0, 30),
    )

    assert result == -7.5


def test_rate_band_get_amount_at_datetime_applies_calculation_factor_to_variable_rate():
    band = make_band(tariff_rate_id=12, calculation_factor=2.0)
    rate = make_consumption_rate(tariff_rate_id=12, variable_rate_key="monthlySupply")
    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_rate=lambda rate_id: rate),
        variables=SimpleNamespace(lookup=lambda key, dt: 3.5),
    )

    result = ru.rate_band_get_amount_at_datetime(
        band,  # type: ignore[arg-type]
        library,  # type: ignore[arg-type]
        datetime(2025, 1, 1, 0, 30),
    )

    assert result == 7.0


def test_get_rate_consumption_bands_rejects_quantity_key():
    rate = make_consumption_rate(quantity_key="billingMeter")

    with pytest.raises(RateConversionError, match="quantity_key"):
        es.get_rate_consumption_bands_at_datetime(
            rate=rate,  # type: ignore[arg-type]
            scenario=None,  # pyright: ignore[reportArgumentType]
            library=None,  # pyright: ignore[reportArgumentType]
            dt=datetime(2025, 1, 1, 0, 30),
        )


def test_tariff_iter_rates_for_dt_skips_inaccessible_rider_and_records_issue():
    rate = make_rate(tariff_rate_id=9, rate_name="Rider Placeholder", rate_bands=[], rider_id=77)
    tariff = {"rates": [rate]}
    issues: list[tuple[tuple[object, ...], str]] = []

    def get_tariff(tariff_id: int):
        raise TariffAccessDenied(tariff_id)

    library = SimpleNamespace(
        tariffs=SimpleNamespace(get_tariff=get_tariff),
        record_issue=lambda key, message: issues.append((key, message)),
    )

    result = list(
        ru.tariff_iter_rates_for_dt(
            tariff,  # type: ignore[arg-type]
            Scenario(1, 2025, False, {"SUPPLY"}),
            library,  # type: ignore[arg-type]
            datetime(2025, 1, 1, 0, 30),
        )
    )

    assert result == []
    assert issues == [
        (
            ("inaccessible_rider", 9, 77),
            "Skipping inaccessible rider 77 attached to rate 9 (Rider Placeholder)",
        )
    ]


def test_tariff_library_caches_access_denied_tariff_ids():
    calls: list[int] = []

    class DummyTariffsAPI:
        def iter_pages(self, **kwargs):
            calls.append(int(kwargs["search"]))
            response = Response()
            response.status_code = 403
            raise HTTPError(response=response)

    api = SimpleNamespace(tariffs=DummyTariffsAPI())
    library = TariffLibrary(api, LibraryDebugStore())  # type: ignore[arg-type]

    with pytest.raises(TariffAccessDenied):
        library.get_tariff(77)
    with pytest.raises(TariffAccessDenied):
        library.get_tariff(77)

    assert calls == [77]
