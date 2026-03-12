import json
from datetime import date, datetime
from pathlib import Path

from tariff_fetch.urdb.arcadia.library import LibraryDebugStore


def test_library_debug_store_saves_tariff_lookup_and_property(tmp_path: Path):
    store = LibraryDebugStore(tmp_path / "arcadia_library")

    store.save_tariff(
        {
            "tariff_id": 10,
            "master_tariff_id": 20,
            "effective_date": date(2025, 1, 1),
        }  # type: ignore[reportArgumentType]
    )
    store.save_lookups(
        "supplyCharge",
        2025,
        [
            {
                "from_date_time": datetime(2025, 1, 1, 0, 0),
                "to_date_time": datetime(2025, 2, 1, 0, 0),
                "actual_value": 0.1,
                "best_value": None,
                "forecast_value": None,
            }
        ],  # type: ignore[reportArgumentType]
    )
    store.save_property_value("territoryId", ["1", "2"])

    tariff_path = tmp_path / "arcadia_library" / "tariffs" / "master-20_tariff-10_effective-2025-01-01.json"
    lookups_path = tmp_path / "arcadia_library" / "lookups" / "supplyCharge_2025.json"
    property_path = tmp_path / "arcadia_library" / "properties" / "territoryId.json"

    assert json.loads(tariff_path.read_text())["tariff_id"] == 10
    assert json.loads(lookups_path.read_text())[0]["actual_value"] == 0.1
    assert json.loads(property_path.read_text()) == {"key": "territoryId", "value": ["1", "2"]}
