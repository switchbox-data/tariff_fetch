import re

from .types import BandDeterminant, ConsumptionRateDeterminant

_DATE_COL_RE = re.compile(r"^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(\d{4})$")


def is_date_column_name(column_name: str) -> bool:
    return bool(_DATE_COL_RE.match(column_name))


def kwh_multiplier(determinant: ConsumptionRateDeterminant | BandDeterminant) -> float:
    match determinant:
        case "per therm" | "therms":
            return 29.3
        case "per ccf" | "ccf":
            return 29.31
        case "cubic feet":
            return 0.2931
