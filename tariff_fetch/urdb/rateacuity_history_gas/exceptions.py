from typing import final, override


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
