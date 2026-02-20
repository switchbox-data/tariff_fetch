import itertools
from collections.abc import Collection
from math import inf
from typing import cast

from tariff_fetch.urdb.schema import EnergyTier, MonthSchedule, URDBRate

from .history_data import ConsumptionRow, FixedChargeRow, PercentageRow, Row


def build_urdb(rows: Collection[Row], include_taxes: bool) -> URDBRate:
    energy_schedule = _build_energy_schedule_raw(rows, include_taxes)
    static_rate = _build_static_charges(rows)
    return {**energy_schedule, **static_rate}


def _build_energy_schedule_raw(rows: Collection[Row], include_taxes: bool) -> URDBRate:
    month_bands: list[tuple[tuple[float, float], ...]] = []
    monthly_taxes = _get_monthly_taxes(rows)
    for month in range(0, 12):
        tax = monthly_taxes[month] if include_taxes else 1
        bands = [
            (row.start_kwh, row.end_kwh, row.month_value_kwh(month) * tax)
            for row in rows
            if isinstance(row, ConsumptionRow)
        ]
        band_limits = sorted({*(l1 for l1, _, _ in bands), *(l2 for _, l2, _ in bands)})
        summed_bands = tuple(
            (limit, sum(rate for low, high, rate in bands if low < limit <= high)) for limit in band_limits
        )
        # round bands
        summed_bands = tuple(
            (round(limit) if limit != inf else inf, round(max(0, value), 6)) for limit, value in summed_bands
        )
        # join bands
        summed_bands = [
            *(this for this, next_ in itertools.pairwise(summed_bands) if this[1] != next_[1] and this[0] != 0),
            summed_bands[-1],
        ]
        # remove <30kwh difference bands
        # Most bands on rateacuity are in therms or ccf, which causes small gaps
        # when converting them to kwh, so this way we attempt to circumvent this.
        # It's not ideal but will do for now
        summed_bands = [
            summed_bands[0],
            *(this for prev, this in itertools.pairwise(summed_bands) if this[0] - prev[0] > 30),
        ]
        month_bands.append(tuple(summed_bands))
    month_bands_unique = list(set(month_bands))
    energy_weekday_schedule = cast(MonthSchedule, tuple(tuple([month_bands_unique.index(b)] * 24) for b in month_bands))
    energy_weekend_schedule = energy_weekday_schedule
    energy_rate_structure = [[_band_tuple_to_tier(br) for br in mb if br != (0, 0)] for mb in month_bands_unique]
    return {
        "energyratestructure": energy_rate_structure,
        "energyweekdayschedule": energy_weekday_schedule,
        "energyweekendschedule": energy_weekend_schedule,
    }


def _build_static_charges(rows: Collection[Row]) -> URDBRate:
    fixed_charge_sum = (
        sum(row.month_value(month) for row in rows if isinstance(row, FixedChargeRow) for month in range(0, 12)) / 12
    )
    return {"fixedchargefirstmeter": fixed_charge_sum, "fixedchargeunits": "$/month"}


def _get_monthly_taxes(rows: Collection[Row]) -> list[float]:
    return [
        1 + sum(row.month_value_float(month) for row in rows if isinstance(row, PercentageRow))
        for month in range(0, 12)
    ]


def _band_tuple_to_tier(band_tuple: tuple[float, float]) -> EnergyTier:
    limit, rate = band_tuple
    if limit == inf:
        return {"rate": rate, "unit": "kWh"}
    return {"rate": rate, "unit": "kWh", "max": limit}
