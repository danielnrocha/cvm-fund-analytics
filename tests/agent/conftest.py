import pytest
from pydantic_ai import models


@pytest.fixture(autouse=True)
def disable_live_models(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


def pytest_addoption(parser):
    parser.addoption(
        "--require-integration", action="store_true",
        help="Fail the full agent suite if any test is skipped",
    )


def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption("--require-integration"):
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        raise pytest.UsageError("--require-integration requires the terminal reporter")
    skipped = len(reporter.stats.get("skipped", []))
    if skipped:
        reporter.write_line(f"Required agent suite skipped {skipped} test(s)")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
