from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, cast, overload

import questionary
import typer

T = TypeVar("T")
_ValidateStr = Callable[[str], bool | str]
_ValidateObjects = Callable[[list[object]], bool | str]


class _Question(Protocol):
    def ask(self) -> object | None: ...


class _SelectFactory(Protocol):
    def __call__(
        self,
        message: str,
        choices: Sequence[object],
        default: object | None = None,
        use_shortcuts: bool = False,
        use_arrow_keys: bool = True,
        use_jk_keys: bool = True,
        use_search_filter: bool = False,
        show_description: bool = True,
    ) -> _Question: ...


class _CheckboxFactory(Protocol):
    def __call__(
        self,
        message: str,
        choices: Sequence[object],
        validate: _ValidateObjects = ...,
        use_jk_keys: bool = True,
        use_search_filter: bool = False,
        show_description: bool = True,
    ) -> _Question: ...


class _TextFactory(Protocol):
    def __call__(
        self,
        message: str,
        default: str = "",
        validate: _ValidateStr = ...,
    ) -> _Question: ...


class _ConfirmFactory(Protocol):
    def __call__(self, message: str, default: bool = True, auto_enter: bool = True) -> _Question: ...


class _PathFactory(Protocol):
    def __call__(
        self,
        message: str,
        default: str = "",
        validate: _ValidateStr = ...,
        file_filter: Callable[[str], bool] | None = None,
    ) -> _Question: ...


_select_impl = cast(_SelectFactory, questionary.select)
_checkbox_impl = cast(_CheckboxFactory, questionary.checkbox)
_text_impl = cast(_TextFactory, questionary.text)
_confirm_impl = cast(_ConfirmFactory, questionary.confirm)
_path_impl = cast(_PathFactory, questionary.path)
_no_input = False


def _validate_str_always(_: str) -> bool | str:
    return True


def _validate_objects_always(_: list[object]) -> bool | str:
    return True


def set_no_input(enabled: bool) -> None:
    global _no_input
    _no_input = enabled


def is_no_input() -> bool:
    return _no_input


@dataclass(frozen=True)
class Choice(Generic[T]):
    title: str
    value: T | None = None
    disabled: str | None = None
    checked: bool | None = False
    shortcut_key: str | bool | None = True
    description: str | None = None


@dataclass(frozen=True)
class Separator:
    line: str | None = None


class Prompt(Generic[T]):
    _question: _Question
    _message: str

    def __init__(self, question: _Question, *, message: str) -> None:
        self._question = question
        self._message = message

    def ask(self) -> T | None:
        if _no_input:
            typer.echo(f"Prompt requires interactive input but --no-input was set: {self._message}", err=True)
            raise typer.Exit(code=1)
        return cast(T | None, self._question.ask())

    def ask_or_exit(self, code: int = 1) -> T:
        result = self.ask()
        if result is None:
            raise typer.Exit(code=code)
        return result


def _convert_choice(choice: str | Choice[T] | Separator) -> object:
    if isinstance(choice, Choice):
        return questionary.Choice(
            title=choice.title,
            value=choice.value,
            disabled=choice.disabled,
            checked=choice.checked,
            shortcut_key=choice.shortcut_key,
            description=choice.description,
        )
    if isinstance(choice, Separator):
        return questionary.Separator(line=choice.line)
    return choice


@overload
def select(
    message: str,
    choices: Sequence[str | Separator],
    *,
    default: str | None = None,
    use_shortcuts: bool = False,
    use_arrow_keys: bool = True,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[str]: ...


@overload
def select(
    message: str,
    choices: Sequence[Choice[T] | Separator],
    *,
    default: None = None,
    use_shortcuts: bool = False,
    use_arrow_keys: bool = True,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[T]: ...


def select(
    message: str,
    choices: Sequence[str | Choice[T] | Separator],
    *,
    default: str | None = None,
    use_shortcuts: bool = False,
    use_arrow_keys: bool = True,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[str] | Prompt[T]:
    return Prompt(
        _select_impl(
            message=message,
            choices=[_convert_choice(choice) for choice in choices],
            default=default,
            use_shortcuts=use_shortcuts,
            use_arrow_keys=use_arrow_keys,
            use_jk_keys=use_jk_keys,
            use_search_filter=use_search_filter,
            show_description=show_description,
        ),
        message=message,
    )


@overload
def checkbox(
    message: str,
    choices: Sequence[str | Separator],
    *,
    validate: _ValidateObjects = _validate_objects_always,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[list[str]]: ...


@overload
def checkbox(
    message: str,
    choices: Sequence[Choice[T] | Separator],
    *,
    validate: _ValidateObjects = _validate_objects_always,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[list[T]]: ...


def checkbox(
    message: str,
    choices: Sequence[str | Choice[T] | Separator],
    *,
    validate: _ValidateObjects = _validate_objects_always,
    use_jk_keys: bool = True,
    use_search_filter: bool = False,
    show_description: bool = True,
) -> Prompt[list[str]] | Prompt[list[T]]:
    return Prompt(
        _checkbox_impl(
            message=message,
            choices=[_convert_choice(choice) for choice in choices],
            validate=validate,
            use_jk_keys=use_jk_keys,
            use_search_filter=use_search_filter,
            show_description=show_description,
        ),
        message=message,
    )


def text(message: str, *, default: str = "", validate: _ValidateStr = _validate_str_always) -> Prompt[str]:
    return Prompt(_text_impl(message=message, default=default, validate=validate), message=message)


def confirm(message: str, *, default: bool = True, auto_enter: bool = True) -> Prompt[bool]:
    return Prompt(_confirm_impl(message=message, default=default, auto_enter=auto_enter), message=message)


def path(
    message: str,
    *,
    default: str = "",
    validate: _ValidateStr = _validate_str_always,
    file_filter: Callable[[str], bool] | None = None,
) -> Prompt[str]:
    return Prompt(
        _path_impl(message=message, default=default, validate=validate, file_filter=file_filter), message=message
    )
