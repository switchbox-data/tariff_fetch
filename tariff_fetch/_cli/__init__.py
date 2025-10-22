import os
from datetime import datetime
from pathlib import Path

import questionary
from pathvalidate import sanitize_filename
from rich.console import Console

console = Console()


def prompt_filename(output_folder: Path, suggested_filename: str, extension: str) -> Path:
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

    return Path(
        questionary.path(
            message="Path to save the results",
            default=filepath.as_posix(),
            file_filter=lambda _: Path(_).suffix == extension,
            validate=lambda _: (not os.path.exists(_)) or "A file with that name already exists",
        ).ask()
    )
