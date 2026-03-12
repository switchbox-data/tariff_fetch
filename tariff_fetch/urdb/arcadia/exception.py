from datetime import date
from typing import final

from typing_extensions import override

from tariff_fetch.arcadia.schema.tariffrate import TariffRateExtended


class ConversionError(Exception):
    pass


@final
class TariffConversionError(ConversionError):
    def __init__(self, master_tariff_id: int, msg: str) -> None:
        self.master_tariff_id = master_tariff_id
        self.msg = msg
        super().__init__(msg)


@final
class RateConversionError(ConversionError):
    def __init__(self, rate: TariffRateExtended, msg: str) -> None:
        self.rate = rate
        self.msg = msg
        super().__init__(msg)


class TariffNotFoundError(ConversionError):
    pass


@final
class TariffNotFoundById(ConversionError):
    def __init__(self, tariff_id: int) -> None:
        self.tariff_id = tariff_id
        super().__init__()

    @override
    def __str__(self) -> str:
        return f"Tariff with id={self.tariff_id} not found"


@final
class TariffNotFoundByDate(ConversionError):
    def __init__(self, master_tariff_id: int, dt: date) -> None:
        self.master_tariff_id = master_tariff_id
        self.dt = dt
        super().__init__()

    @override
    def __str__(self) -> str:
        return f"Tariff version not found for master_tariff_id={self.master_tariff_id} date={self.dt}"
