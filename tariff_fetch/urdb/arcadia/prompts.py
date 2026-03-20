"""Interactive prompts for Arcadia conversion scenario and property inputs."""

from datetime import date
from typing import cast, get_args

from tariff_fetch import questionary_typed as q
from tariff_fetch._cli import console
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
    """Prompt for the Arcadia charge classes to include in conversion."""

    choices = cast(tuple[RateChargeClass, ...], get_args(RateChargeClass))
    result_raw = q.checkbox(
        "Select charge classes",
        choices=[
            q.Choice(
                title=choice,
                value=choice,
                checked=True,
            )
            for choice in choices
        ],
    ).ask()
    if result_raw is None:
        return None
    return cast(set[RateChargeClass], set(result_raw))


def prompt_string(tariff_property: TariffPropertyStandard) -> str | None:
    """Prompt for a string-valued Arcadia tariff property."""

    _print_property_prompt_context(tariff_property)
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    return q.text(
        _get_property_title(tariff_property),
        default=default_value or "",
    ).ask_or_exit()


def prompt_choice(tariff_property: TariffPropertyStandard) -> list[str] | None:
    """Prompt for a multi-select Arcadia CHOICE property."""

    _print_property_prompt_context(tariff_property)
    if tariff_property["is_default"]:
        default_value_raw = tariff_property.get("property_value")
        default_value = {item.strip() for item in (default_value_raw or "").split(",")}
    else:
        default_value: set[str] = set()
    if not (choices := tariff_property.get("choices")):
        raise ValueError("Expected a list of choices for CHOICE property")
    return q.checkbox(
        _get_property_title(tariff_property),
        choices=[
            q.Choice(title=item["display_value"], value=item["value"], checked=item["value"] in default_value)
            for item in choices
        ],
    ).ask_or_exit()


def prompt_boolean(tariff_property: TariffPropertyStandard) -> bool | None:
    """Prompt for a boolean Arcadia tariff property."""

    _print_property_prompt_context(tariff_property)
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = True if default_value == "true" else (False if default_value == "false" else None)
    result = q.confirm(
        _get_property_title(tariff_property), default=default_value if default_value is not None else False
    ).ask_or_exit()
    return result


def prompt_date(tariff_property: TariffPropertyStandard) -> date | None:  # pyright: ignore[reportUnusedParameter]
    """Placeholder for date property prompting, which is not implemented yet."""

    raise NotImplementedError()


def prompt_decimal(tariff_property: TariffPropertyStandard) -> float | None:
    """Prompt for a decimal-valued Arcadia tariff property."""

    _print_property_prompt_context(tariff_property)
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = float(default_value) if default_value else None

    result_str = q.text(
        _get_property_title(tariff_property),
        default=str(default_value) if default_value else "",
        validate=_is_float,
    ).ask_or_exit()
    return float(result_str)


def prompt_integer(tariff_property: TariffPropertyStandard) -> float | None:
    """Prompt for an integer-valued Arcadia tariff property."""

    _print_property_prompt_context(tariff_property)
    default_value = tariff_property.get("property_value") if tariff_property["is_default"] else None
    default_value = int(default_value) if default_value else None

    result_str = q.text(
        _get_property_title(tariff_property),
        default=str(default_value) if default_value else "",
        validate=_is_int,
    ).ask_or_exit()
    return float(result_str)


def prompt_demand(tariff_property: TariffPropertyStandard) -> float | None:
    """Prompt for a demand-valued Arcadia tariff property."""

    return prompt_decimal(tariff_property)


def _is_float(value: str) -> bool:
    """Return whether a string can be parsed as a float."""

    try:
        _ = float(value)
    except ValueError:
        return False
    return True


def _is_int(value: str) -> bool:
    """Return whether a string can be parsed as an integer."""

    try:
        _ = int(value)
    except ValueError:
        return False
    return True


def _get_property_title(tariff_property: TariffPropertyStandard) -> str:
    """Return the primary property label shown in the actual prompt."""

    return f"[{tariff_property['key_name']}] {tariff_property['display_name']}"


def _print_property_prompt_context(tariff_property: TariffPropertyStandard) -> None:
    """Print styled property metadata before prompting for its value."""

    description = tariff_property["description"]
    console.print(f"[dim]{description}[/dim]")
