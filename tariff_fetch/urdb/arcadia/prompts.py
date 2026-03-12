from datetime import date
from typing import cast, get_args

import questionary

from tariff_fetch.arcadia.schema.common import RateChargeClass
from tariff_fetch.arcadia.schema.tariffproperty import TariffPropertyStandard

# def prompt_scenario(master_tariff_id: int, year: int, apply_percentages: bool) -> Scenario | None:
#    result_charge_classes = prompt_charge_classes()
#    if result_charge_classes is None:
#        return None
#
#    properties = tariff.get("properties", [])
#    result_property_values: dict[str, PropertyValues] = {}
#    for tariff_property in properties:
#        key = tariff_property["key_name"]
#        if key == "chargeClass":
#            continue
#        if key == "consumption":
#            continue
#        value = prompt_property(tariff_property)
#        if value is None:
#            return None
#        result_property_values[key] = value
#    return Scenario(
#        tariff,
#        year=year,
#        apply_percentages=apply_percentages,
#        charge_classes=result_charge_classes,
#        properies=result_property_values,
#    )


def prompt_charge_classes() -> set[RateChargeClass] | None:
    choices = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))
    result_raw = cast(
        list[RateChargeClass] | None,
        questionary.checkbox(
            "Select charge classes",
            choices=[
                questionary.Choice(
                    title=choice,
                    value=choice,
                    checked=True,
                )
                for choice in choices
            ],
        ).ask(),
    )
    if result_raw is None:
        return None
    return set(result_raw)


def prompt_string(tariff_property: TariffPropertyStandard) -> str | None:
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    return cast(
        str | None,
        questionary.text(
            _get_property_msg(tariff_property),
            default=default_value or "",
        ).ask(),
    )


def prompt_choice(tariff_property: TariffPropertyStandard) -> list[str] | None:
    if tariff_property["is_default"]:
        default_value_raw = tariff_property.get("property_value")
        default_value = {item.strip() for item in (default_value_raw or "").split(",")}
    else:
        default_value: set[str] = set()
    if not (choices := tariff_property.get("choices")):
        raise ValueError("Expected a list of choices for CHOICE property")
    return cast(
        list[str] | None,
        questionary.checkbox(
            _get_property_msg(tariff_property),
            choices=[
                questionary.Choice(
                    title=item["display_value"], value=item["value"], checked=item["value"] in default_value
                )
                for item in choices
            ],
        ).ask(),
    )


def prompt_boolean(tariff_property: TariffPropertyStandard) -> bool | None:
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = True if default_value == "true" else (False if default_value == "false" else None)
    result = cast(
        bool | None,
        questionary.confirm(
            _get_property_msg(tariff_property), default=default_value if default_value is not None else False
        ).ask(),
    )
    return result


def prompt_date(tariff_property: TariffPropertyStandard) -> date | None:  # pyright: ignore[reportUnusedParameter]
    raise NotImplementedError()


def prompt_decimal(tariff_property: TariffPropertyStandard) -> float | None:
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = float(default_value) if default_value else None

    result_str = cast(
        str | None,
        questionary.text(
            _get_property_msg(tariff_property),
            default=str(default_value) if default_value else "",
            validate=_is_float,
        ).ask(),
    )
    if result_str is None:
        return None
    return float(result_str)


def prompt_integer(tariff_property: TariffPropertyStandard) -> float | None:
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = int(default_value) if default_value else None

    result_str = cast(
        str | None,
        questionary.text(
            _get_property_msg(tariff_property),
            default=str(default_value) if default_value else "",
            validate=_is_int,
        ).ask(),
    )
    if result_str is None:
        return None
    return float(result_str)


def prompt_demand(tariff_property: TariffPropertyStandard) -> float | None:
    return prompt_decimal(tariff_property)


def _is_float(value: str) -> bool:
    try:
        _ = float(value)
    except ValueError:
        return False
    return True


def _is_int(value: str) -> bool:
    try:
        _ = int(value)
    except ValueError:
        return False
    return True


def _get_property_msg(tariff_property: TariffPropertyStandard) -> str:
    title = tariff_property["display_name"]
    description = tariff_property["description"]
    return f"{title} ({description})"
