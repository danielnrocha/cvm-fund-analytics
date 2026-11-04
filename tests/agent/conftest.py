import pytest
from pydantic_ai import models


@pytest.fixture(autouse=True)
def disable_live_models(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


def pytest_addoption(parser):
    parser.addoption(
        "--require-integration", action="store_true",
        help="Fail the full agent suite if any test is skipped, xfailed, or deselected",
    )


def pytest_sessionfinish(session, exitstatus):
    if not session.config.getoption("--require-integration"):
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        raise pytest.UsageError("--require-integration requires the terminal reporter")
    for outcome in ("skipped", "xfailed", "deselected"):
        count = len(reporter.stats.get(outcome, []))
        if count:
            reporter.write_line(f"Required agent suite {outcome} {count} test(s)")
            if exitstatus == pytest.ExitCode.OK:
                session.exitstatus = pytest.ExitCode.TESTS_FAILED
