import os
from datetime import datetime
from pathlib import Path

from pathvalidate import sanitize_filename
from rich.console import Console

from tariff_fetch import questionary_typed as q

console = Console()


def _json_file_filter(path: str) -> bool:
    return Path(path).suffix == ".json"


def _file_filter_for_extension(extension: str):
    def _file_filter(path: str) -> bool:
        return Path(path).suffix == f".{extension}"

    return _file_filter


def _validate_new_path(path: str) -> bool | str:
    return (not os.path.exists(path)) or "A file with that name already exists"


def prompt_filename(output_folder: Path, suggested_filename: str, extension: str) -> Path | None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    suggested_filename = sanitize_filename(f"{suggested_filename}_{date_str}")
    if output_folder.exists():
        existing_filenames = set(output_folder.iterdir())
        filepath = next(
            _
            for i in range(0xFFFFFF)
            if (_ := output_folder.joinpath(f"{suggested_filename}-{i}{os.extsep}{extension}"))
            not in existing_filenames
        )
    else:
        filepath = output_folder.joinpath(f"{suggested_filename}-0{os.extsep}{extension}")

    result = q.path(
        message="Path to save the results",
        default=filepath.as_posix(),
        file_filter=_json_file_filter if extension == "json" else _file_filter_for_extension(extension),
        validate=_validate_new_path,
    )
    value = result.ask()
    if value is None:
        return None
    return Path(value)
