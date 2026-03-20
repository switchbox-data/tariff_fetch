from datetime import date
from types import SimpleNamespace
from typing import Any, cast

from tariff_fetch.urdb.arcadia.library import Library


def test_library_coerces_cli_property_overrides_to_expected_types():
    library = Library(
        api=object(),  # type: ignore[arg-type]
        properties={
            "territoryId": "1,2",
            "netMetering": "true",
            "serviceStart": "2025-01-02",
            "baselineKwh": "10.5",
            "occupants": "3",
        },
    )
    cast(Any, library).tariffs = SimpleNamespace(
        get_property=lambda key: {
            "territoryId": {"key_name": "territoryId", "display_name": "Territory", "data_type": "CHOICE"},
            "netMetering": {"key_name": "netMetering", "display_name": "Net Metering", "data_type": "BOOLEAN"},
            "serviceStart": {"key_name": "serviceStart", "display_name": "Service Start", "data_type": "DATE"},
            "baselineKwh": {"key_name": "baselineKwh", "display_name": "Baseline kWh", "data_type": "DECIMAL"},
            "occupants": {"key_name": "occupants", "display_name": "Occupants", "data_type": "INTEGER"},
        }[key]
    )

    assert library.get_property("territoryId", "CHOICE") == ["1", "2"]
    assert library.get_property("netMetering", "BOOLEAN") is True
    assert library.get_property("serviceStart", "DATE") == date(2025, 1, 2)
    assert library.get_property("baselineKwh", "DECIMAL") == 10.5
    assert library.get_property("occupants", "INTEGER") == 3


def test_library_accepts_property_and_choice_display_aliases():
    library = Library(
        api=object(),  # type: ignore[arg-type]
        properties={"Territory": ["Primary Territory", "2"]},
    )
    cast(Any, library).tariffs = SimpleNamespace(
        get_property=lambda key: {
            "territoryId": {
                "key_name": "territoryId",
                "display_name": "Territory",
                "data_type": "CHOICE",
                "choices": [
                    {"value": "1", "display_value": "Primary Territory", "data_value": "1"},
                    {"value": "2", "display_value": "Secondary Territory", "data_value": "2"},
                ],
            }
        }[key]
    )

    assert library.get_property("territoryId", "CHOICE") == ["1", "2"]
