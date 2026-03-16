from typing import final

from typing_extensions import override


@final
class EmptyBandsError(ValueError):
    @override
    def __str__(self) -> str:
        return "Empty monthly bands"


@final
class IncorrectDataframeSchemaMonths(ValueError):
    @override
    def __str__(self) -> str:
        return "Incorrect months"


@final
class IncorrectDataframeSchemaMultipleYears(ValueError):
    @override
    def __str__(self) -> str:
        return "Multiple years in the dataframe"
