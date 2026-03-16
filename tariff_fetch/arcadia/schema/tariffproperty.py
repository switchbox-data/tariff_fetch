from typing import Literal, NotRequired

from pydantic.alias_generators import to_camel
from typing_extensions import TypedDict

TariffPropertyFormulaType = Literal["FORMULA"]


TariffPropertyPrunedDataType = Literal[
    "STRING",
    "CHOICE",
    "BOOLEAN",
    "DATE",
    "DECIMAL",
    "INTEGER",
    "DEMAND",
]

TariffPropertyDataType = Literal[
    TariffPropertyPrunedDataType,
    TariffPropertyFormulaType,
]

TariffPropertyCategory = Literal[
    "APPLICABILITY",
    "RATE_CRITERIA",
    "BENEFIT",
    "DATA_REPUTATION",
    "SERVICE_TERMS",
]


TariffPropertyPeriod = Literal[
    "ON_PEAK",
    "PARTIAL_PEAK",
    "OFF_PEAK",
    "CRITICAL_PEAK",
    "SUPER_ON_PEAK",
    "ALL",  # Undocumented
]


class TariffPropertyChoice(TypedDict):
    value: str
    "Machine readable option value"
    display_value: str
    "Human readable value shown to end users"
    data_value: str
    likelihood: NotRequired[float | None]


class TariffPropertyMinimalFields(TypedDict):
    quantity_key: NotRequired[str | None]
    quantity_unit: NotRequired[str | None]
    key_name: str
    display_name: str
    keyspace: str
    family: str
    description: str
    data_type: TariffPropertyDataType
    property_types: TariffPropertyCategory


class TariffPropertyStandardFields(TypedDict):
    period: NotRequired[TariffPropertyPeriod]
    operator: str | None
    property_value: NotRequired[str]
    minValue: NotRequired[str | float | int]
    maxValue: NotRequired[str | float | int]
    choices: NotRequired[list[TariffPropertyChoice]]
    formula_detail: NotRequired[str]
    is_default: bool


class TariffPropertyMinimal(TariffPropertyMinimalFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "allow"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa


class TariffPropertyStandard(TariffPropertyMinimalFields, TariffPropertyStandardFields):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "allow"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
