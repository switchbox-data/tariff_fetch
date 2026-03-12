"""Converter-specific exception types for Arcadia to URDB translation."""

from datetime import date
from typing import final

from typing_extensions import override

from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended


class ConversionError(Exception):
    """Base exception for Arcadia-to-URDB conversion failures."""


@final
class TariffConversionError(ConversionError):
    """Conversion error scoped to a master Arcadia tariff."""

    def __init__(self, master_tariff_id: int, msg: str) -> None:
        self.master_tariff_id = master_tariff_id
        self.msg = msg
        super().__init__(msg)


@final
class RateConversionError(ConversionError):
    """Conversion error scoped to a specific Arcadia tariff rate."""

    def __init__(self, rate: TariffRateExtended, msg: str) -> None:
        self.rate = rate
        self.msg = msg
        super().__init__(msg)


class TariffNotFoundError(ConversionError):
    """Base exception for tariff lookup misses."""


@final
class TariffAccessDenied(ConversionError):
    """Raised when Arcadia denies access to a tariff id."""

    def __init__(self, tariff_id: int) -> None:
        self.tariff_id = tariff_id
        super().__init__()

    @override
    def __str__(self) -> str:
        return f"Access denied for tariff id={self.tariff_id}"


@final
class TariffNotFoundById(TariffNotFoundError):
    """Raised when a tariff version cannot be found by Arcadia tariff id."""

    def __init__(self, tariff_id: int) -> None:
        self.tariff_id = tariff_id
        super().__init__()

    @override
    def __str__(self) -> str:
        return f"Tariff with id={self.tariff_id} not found"


@final
class TariffNotFoundByDate(TariffNotFoundError):
    """Raised when no tariff version is effective for a requested date."""

    def __init__(self, master_tariff_id: int, dt: date) -> None:
        self.master_tariff_id = master_tariff_id
        self.dt = dt
        super().__init__()

    @override
    def __str__(self) -> str:
        return f"Tariff version not found for master_tariff_id={self.master_tariff_id} date={self.dt}"
