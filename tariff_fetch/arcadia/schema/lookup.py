from datetime import datetime
from typing import NotRequired, TypedDict

from pydantic.alias_generators import to_camel


class Lookup(TypedDict):
    __pydantic_config__ = {"alias_generator": to_camel, "extra": "allow"}  # pyright: ignore[reportGeneralTypeIssues, reportUnannotatedClassAttribute]  # noqa
    lookup_id: int
    """The unique ID for this lookup value entry in the lookup table"""
    property_key: str
    """The unique name for the property this lookup belongs to"""
    sub_property_key: NotRequired[str]
    """Sub-property this lookup value applies to (when needed, e.g., wholesale index node or zone)"""
    from_date_time: datetime
    to_date_time: datetime | None
    best_value: float | None
    """Best kWh/kW price for the property key for the date range"""
    best_accuracy: float | None
    """Reserved for future use"""
    actual_value: float | None
    """Actual kWh/kW price for the property key for the date range"""
    """kWh/kW price forecasted by the utility for the property key for the date range"""
    lse_forecast_value: float | None
    lse_forecast_accuracy: float | None
    """Reserved for future use"""
    forecast_value: float | None
    """kWh/kW price forecasted by Arcadia for the property key for the date range based on previous values"""
    forecast_accuracy: float | None
    """Reserved for future use"""
