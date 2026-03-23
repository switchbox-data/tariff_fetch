from pathlib import Path
from types import SimpleNamespace

import tenacity

from tariff_fetch._cli import rateacuity
from tariff_fetch._cli.types import Utility


class _FakeAttempt:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeRetrying:
    def __iter__(self):
        yield _FakeAttempt()


def test_process_rateacuity_prints_replay_command(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(rateacuity, "load_dotenv", lambda: None)
    monkeypatch.setattr(rateacuity, "os", SimpleNamespace(getenv=lambda key: "set"))
    monkeypatch.setattr(
        rateacuity,
        "tenacity",
        SimpleNamespace(
            Retrying=lambda **kwargs: _FakeRetrying(),
            stop_after_attempt=tenacity.stop_after_attempt,
            retry_if_exception_type=tenacity.retry_if_exception_type,
        ),
    )

    class FakeScrapingState:
        def __init__(self):
            self._current_tariff = ""

        def login(self, username, password):
            return self

        def electric(self):
            return self

        def benchmark_all(self):
            return self

        def select_state(self, state):
            return self

        def get_utilities(self):
            return ["Consolidated Edison Company of New York"]

        def select_utility(self, utility):
            return self

        def get_schedules(self):
            return ["Residential Service", "Time of Use"]

        def select_schedule(self, tariff):
            self._current_tariff = tariff
            return self

        def as_sections(self):
            return [{"section": self._current_tariff}]

        def back_to_selections(self):
            return self

    class FakeContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(rateacuity, "create_context", lambda: FakeContext())
    monkeypatch.setattr(rateacuity, "LoginState", lambda context: FakeScrapingState())
    monkeypatch.setattr(
        rateacuity,
        "q",
        SimpleNamespace(
            confirm=lambda message: SimpleNamespace(ask_or_exit=lambda: True),
            checkbox=lambda **kwargs: SimpleNamespace(ask_or_exit=lambda: ["Residential Service", "Time of Use"]),
            select=lambda **kwargs: SimpleNamespace(ask_or_exit=lambda: "unused"),
        ),
    )
    monkeypatch.setattr(rateacuity, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json")
    monkeypatch.setattr(rateacuity.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))
    monkeypatch.setattr(rateacuity.console, "log", lambda *args, **kwargs: None)

    rateacuity.process_rateacuity(
        output_folder=tmp_path,
        state="ny",
        utility=Utility(eia_id=123, name="Consolidated Edison"),
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch ni rateacuity ")]
    assert replay_lines == [
        "tariff-fetch ni rateacuity eia-id 123 --tariff 'Residential Service' --tariff 'Time of Use'"
    ]
