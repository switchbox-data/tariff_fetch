from collections.abc import Collection, Iterator
from datetime import date, datetime
from math import inf

from tariff_fetch.arcadia.schema.common import RateChargeClass, RateUnit
from tariff_fetch.arcadia.schema.season import SeasonExtended
from tariff_fetch.arcadia.schema.tariff import TariffExtended
from tariff_fetch.arcadia.schema.tariffrate import TariffRateBand, TariffRateExtended
from tariff_fetch.arcadia.schema.timeofuse import Period, TimeOfUseExtended
from tariff_fetch.urdb.arcadia.library import Library

from .exception import RateConversionError
from .scenario import Scenario

# ================================
# Tariff
# ================================


def tariff_iter_rates_for_dt(
    tariff: TariffExtended,
    scenario: Scenario,
    library: Library,
    dt: datetime,
) -> Iterator[TariffRateExtended]:
    rates = tariff.get("rates", [])
    for rate in rates:
        if not rate_is_applied_to_scenario(rate, scenario, library):
            continue
        if not rate_is_applied_to_datetime(rate, dt):
            continue
        if rate["rate_bands"]:
            yield rate
        elif rider_id := rate.get("rider_id"):
            rider_tariff = library.tariffs.get_tariff(rider_id)
            yield from tariff_iter_rates_for_dt(rider_tariff, scenario, library, dt)


# ================================
# Rate
# ================================


def rate_is_applied_to_scenario(
    rate: TariffRateExtended,
    scenario: Scenario,
    library: Library,
) -> bool:
    if not rate_is_applied_to_charge_classes(rate, scenario.charge_classes):
        return False
    if (territory := rate.get("territory")) is not None:
        territory_id = territory["territory_id"]
        territory_ids = library.get_choice_property_as_ints("territoryId")
        if territory_id not in territory_ids:
            return False

    return True


def rate_is_applied_to_charge_classes(rate: TariffRateExtended, charge_classes: Collection[RateChargeClass]) -> bool:
    if (rate_charge_classes := rate.get("charge_class")) is None:
        return True
    return not set(rate_charge_classes).isdisjoint(charge_classes)


def rate_is_applied_to_datetime(rate: TariffRateExtended, dt: datetime) -> bool:
    if (season := rate.get("season")) and not season_is_datetime_within(season, dt):
        return False
    if (tou := rate.get("time_of_use")) and not time_of_use_is_datetime_within(tou, dt):
        return False
    return True


def rate_filter_bands(rate: TariffRateExtended, scenario: Scenario, library: Library) -> list[TariffRateBand]:
    result: list[TariffRateBand] = []
    for band in rate.get("rate_bands"):
        if band.get("has_demand_limit"):
            raise RateConversionError(rate, "Bands with demand limits are not supported")
        if band.get("demand_upper_limit"):
            raise RateConversionError(rate, "Bands with demand limits are not supported")
        if band.get("has_property_limit"):
            raise RateConversionError(rate, "Bands with property limits are not supported")
        if band.get("property_upper_limit"):
            raise RateConversionError(rate, "Bands with property limits are not supported")
        if band.get("prev_upper_limit"):
            raise RateConversionError(rate, "Bands with property prev_upper_limit are not supported")
        if band.get("calculation_factor"):
            raise RateConversionError(rate, "Bands with property calculation_factor are not supported")
        if band.get("applicability_formula"):
            raise RateConversionError(rate, "Bands with property applicability_formula are not supported")
        if (applicability_value := band.get("applicability_value")) is not None:
            if (applicability_key := rate.get("applicability_key")) is None:
                raise RateConversionError(rate, "Band has applicability value but rate doesn't have applicability key")
            tariff_property = library.tariffs.get_property(applicability_key)

            if (tariff_property.get("period")) is not None:
                raise RateConversionError(rate, "Period properties are not supported for rate bands")

            if (category := tariff_property["property_types"]) not in {"APPLICABILITY", "RATE_CRITERIA"}:
                raise RateConversionError(rate, f"{category} is not a supported property category for tariff bands")

            operator = tariff_property["operator"]
            if operator != "=":
                raise RateConversionError(rate, "Only `=` operators are supported")
            match tariff_property["data_type"]:
                case "CHOICE":
                    if applicability_value not in library.get_property(applicability_key, "CHOICE"):
                        continue
                case "STRING":
                    if applicability_value != library.get_property(applicability_value, "STRING"):
                        continue
                case "BOOLEAN":
                    match applicability_value:
                        case "true":
                            applicability_value_bool = True
                        case "false":
                            applicability_value_bool = False
                        case _:
                            raise RateConversionError(
                                rate, "Boolean applicability value must be either `true` or `false`"
                            )
                    if applicability_value_bool != library.get_property(applicability_key, "BOOLEAN"):
                        continue
                case _:
                    raise RateConversionError(rate, "Unsupported data type for band applicabiltiy properties")
        result.append(band)
    return result


def rate_get_band_units(rate: TariffRateExtended) -> set[RateUnit]:
    return {b["rate_unit"] for b in rate.get("rate_bands", [])}


# ================================
# Rate Band
# ================================
def band_consumption_upper_limit(band: TariffRateBand) -> float:
    return band.get("consumption_upper_limit") or inf


def rate_band_get_amount_at_datetime(band: TariffRateBand, library: Library, dt: datetime) -> float:
    rate_id = band["tariff_rate_id"]
    rate = library.tariffs.get_rate(rate_id)
    mp = -1 if band["is_credit"] else 1
    if (variable_rate_key := rate.get("variable_rate_key")) is None:
        return band["rate_amount"] * mp
    return library.variables.lookup(variable_rate_key, dt) * mp


# ================================
# Time of Use
# ================================


def time_of_use_is_datetime_within(
    tou: TimeOfUseExtended,
    dt: datetime,
) -> bool:
    season = tou.get("season")
    if season and not season_is_datetime_within(season, dt):
        return False

    return any(period_is_datetime_within(period, dt) for period in tou["tou_periods"])


# ================================
# Time of Use - Period
# ================================


def period_is_datetime_within(
    period: Period,
    dt: datetime,
) -> bool:
    return (
        period["from_day_of_week"] <= dt.weekday() <= period["to_day_of_week"]
        and period["from_hour"] <= dt.hour <= period["to_hour"]
        and period["from_minute"] <= dt.minute <= period["to_minute"]
    )


# ================================
# Season
# ================================


def season_is_datetime_within(
    season: SeasonExtended,
    dt: datetime | date,
) -> bool:
    dt = dt.date() if isinstance(dt, datetime) else dt
    start_month, end_month = season["season_from_month"], season["season_to_month"]
    start_day, end_day = season["season_from_day"], season["season_to_day"]
    start_date = date(dt.year, start_month, start_day)
    end_date = date(dt.year, end_month, end_day)
    if start_date < end_date:
        return start_date <= dt < end_date
    return start_date <= dt or dt < end_date
