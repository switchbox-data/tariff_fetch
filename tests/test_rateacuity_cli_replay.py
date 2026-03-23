from pathlib import Path
from types import SimpleNamespace

import tenacity

from tariff_fetch._cli import rateacuity, rateacuity_gas_urdb
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
    monkeypatch.setattr(
        rateacuity, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
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


def test_process_rateacuity_gas_prints_replay_command(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(rateacuity, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        rateacuity,
        "os",
        SimpleNamespace(
            getenv=lambda key: "set",
        ),
    )
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

        def gas(self):
            return self

        def benchmark_all(self):
            return self

        def select_state(self, state):
            return self

        def get_utilities(self):
            return ["Consolidated Edison Gas"]

        def select_utility(self, utility):
            return self

        def get_schedules(self):
            return ["Firm Gas Service", "Interruptible Gas Service"]

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
            checkbox=lambda **kwargs: SimpleNamespace(
                ask_or_exit=lambda: ["Firm Gas Service", "Interruptible Gas Service"]
            ),
            select=lambda **kwargs: SimpleNamespace(ask_or_exit=lambda: "Consolidated Edison Gas"),
        ),
    )
    monkeypatch.setattr(
        rateacuity, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(rateacuity.console, "print", lambda message, *args, **kwargs: printed.append(str(message)))
    monkeypatch.setattr(rateacuity.console, "log", lambda *args, **kwargs: None)

    rateacuity.process_rateacuity_gas(
        output_folder=tmp_path,
        state="ny",
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch gas ni ")]
    assert replay_lines == [
        "tariff-fetch gas ni ny 'Consolidated Edison Gas' --tariff 'Firm Gas Service' --tariff 'Interruptible Gas Service'"
    ]


def test_process_rateacuity_gas_urdb_prints_replay_commands(monkeypatch, tmp_path: Path):
    printed: list[str] = []

    monkeypatch.setattr(rateacuity_gas_urdb, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        rateacuity_gas_urdb,
        "os",
        SimpleNamespace(getenv=lambda key: "set"),
    )
    monkeypatch.setattr(
        rateacuity_gas_urdb,
        "tenacity",
        SimpleNamespace(
            Retrying=lambda **kwargs: _FakeRetrying(),
            stop_after_attempt=tenacity.stop_after_attempt,
            retry_if_exception_type=tenacity.retry_if_exception_type,
        ),
    )

    class FakeHistoryData:
        def __init__(self, df):
            self.df = df

        def validate_rows(self):
            return []

        def get_unknown_nonempty_columns(self):
            return []

        def rows(self):
            return []

    class FakeScrapingState:
        def __init__(self):
            self._current_tariff = ""

        def login(self, username, password):
            return self

        def gas(self):
            return self

        def history(self):
            return self

        def select_state(self, state):
            return self

        def get_utilities(self):
            return ["Consolidated Edison Gas"]

        def select_utility(self, utility):
            return self

        def get_schedules(self):
            return ["Firm Gas Service", "Interruptible Gas Service"]

        def select_schedule(self, tariff):
            self._current_tariff = tariff
            return self

        def set_enddate(self, dt):
            return self

        def set_number_of_comparisons(self, n):
            return self

        def set_frequency(self, n):
            return self

        def as_dataframe(self):
            return object()

        def back_to_selections(self):
            return self

    class FakeContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    label_answers = iter(["ceg", "custom"])
    sector_answers = iter(["Commercial", "Residential"])
    servicetype_answers = iter(["Delivery", "Bundled"])
    percentage_answers = iter([True, False])

    monkeypatch.setattr(rateacuity_gas_urdb, "create_context", lambda: FakeContext())
    monkeypatch.setattr(rateacuity_gas_urdb, "LoginState", lambda context: FakeScrapingState())
    monkeypatch.setattr(rateacuity_gas_urdb, "HistoryData", FakeHistoryData)
    monkeypatch.setattr(rateacuity_gas_urdb, "_get_percentage_columns", lambda rows: [("Pct", None, 1.0)])
    monkeypatch.setattr(rateacuity_gas_urdb, "build_urdb", lambda rows, apply_percentages: {})
    monkeypatch.setattr(
        rateacuity_gas_urdb,
        "Confirm",
        SimpleNamespace(ask=lambda *args, **kwargs: next(percentage_answers)),
    )
    monkeypatch.setattr(
        rateacuity_gas_urdb,
        "q",
        SimpleNamespace(
            checkbox=lambda **kwargs: SimpleNamespace(
                ask_or_exit=lambda: ["Firm Gas Service", "Interruptible Gas Service"]
            ),
            select=lambda *args, **kwargs: SimpleNamespace(
                ask_or_exit=lambda: (
                    "Consolidated Edison Gas"
                    if kwargs.get("message") == "Select a utility from available choices"
                    else next(
                        sector_answers
                        if args and args[0] == "Sector" and kwargs.get("default") == "Residential"
                        else servicetype_answers
                    )
                )
            ),
            text=lambda *args, **kwargs: SimpleNamespace(ask_or_exit=lambda: next(label_answers)),
        ),
    )
    monkeypatch.setattr(
        rateacuity_gas_urdb, "prompt_filename", lambda output_folder, suggested_filename, ext: tmp_path / "out.json"
    )
    monkeypatch.setattr(
        rateacuity_gas_urdb.console, "print", lambda message, *args, **kwargs: printed.append(str(message))
    )
    monkeypatch.setattr(rateacuity_gas_urdb.console, "log", lambda *args, **kwargs: None)

    rateacuity_gas_urdb.process_rateacuity_gas_urdb(
        output_folder=tmp_path,
        state="ny",
        year=2025,
    )

    replay_lines = [line for line in printed if line.startswith("tariff-fetch gas urdb ni ")]
    assert replay_lines == [
        "tariff-fetch gas urdb ni ny 'Consolidated Edison Gas' --year 2025 --tariff 'Firm Gas Service' --apply-percentages --sector Commercial --servicetype Delivery",
        "tariff-fetch gas urdb ni ny 'Consolidated Edison Gas' --year 2025 --tariff 'Interruptible Gas Service' --label custom",
    ]
