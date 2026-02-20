def comma_separated_str(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [_.strip() for _ in value.split(",")]
    return value
