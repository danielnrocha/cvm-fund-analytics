"""Exercise the deterministic delivery entrypoints without a provider session."""
import os
import shutil
import subprocess
import sys

import pytest

from agent.contracts import QueryIntent
from agent.evals import load_cases, oracle_matches
from test_gateway import ROOT, gateway, mf_executable


QUERY_CASES = {
    case.family: case
    for split in ("development", "holdout")
    for case in load_cases(split)[0]
    if case.oracle is not None
}


@pytest.mark.parametrize(("body", "options", "outcome"), [
    ("pytest.skip('missing runtime')", [], "skipped"),
    ("pytest.xfail('expected missing runtime')", [], "xfailed"),
    ("raise AssertionError('gateway test must run')", ["-k", "still_passes"], "deselected"),
])
def test_required_integration_rejects_omitted_cases(tmp_path, body, options, outcome):
    shutil.copyfile(ROOT / "tests/agent/conftest.py", tmp_path / "conftest.py")
    (tmp_path / "test_integration.py").write_text(
        "import pytest\n\ndef test_still_passes():\n    pass\n"
        f"\ndef test_required_gateway():\n    {body}\n"
    )
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--require-integration", *options],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"Required agent suite {outcome} 1 test" in result.stdout


def test_demo_uses_real_gateway_without_login(gateway, tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), XDG_DATA_HOME=str(tmp_path))
    result = subprocess.run(
        [
            sys.executable, "-m", "agent.cli",
            "--release-root", str(gateway._db.parents[2]),
            "--release-id", gateway._release_id, "--mf", str(gateway._mf),
            "plan-file", "demo/agent-plan.json", "--explain",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=70,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for value in (
        "Mode: deterministic plan file",
        "119385193058.06 (60/60; complete)",
        "4725910556.15 (7554/7560; partial)",
        "Executed SQL",
    ):
        assert value in result.stdout


@pytest.mark.parametrize("family", sorted(QUERY_CASES))
def test_candidate_matches_independent_numeric_oracle(gateway, family):
    case = QUERY_CASES[family]
    decision, = (item for item in case.expected if isinstance(item, QueryIntent))
    assert oracle_matches(gateway.query_metrics(decision), case.oracle)
