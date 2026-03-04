from datetime import date

from tariff_fetch.urdb.schema import URDBRate

from .library import Library
from .scenario import Scenario


def build_metadata(scenario: Scenario, library: Library) -> URDBRate:
    master_tariff_id = scenario.master_tariff_id
    tariff = library.tariffs.get_tariff_at_date(master_tariff_id, date(scenario.year, 1, 1))
    return {"label": tariff["lse_code"], "utility": tariff["lse_name"], "name": tariff["tariff_name"], "country": "USA"}
