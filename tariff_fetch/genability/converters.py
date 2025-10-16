from collections.abc import Iterable


def true_or_false(value: bool) -> str:
    return str(value).lower()


def comma_separated(value: Iterable) -> str:
    return ",".join(value)
