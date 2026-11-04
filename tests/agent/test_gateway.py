import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PRIMARY = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
BASELINE = PRIMARY / "baseline/releases/snapshots/cvm-linux-uat-v3"
MF = PRIMARY / "compatibility/dbt-v2-metricflow/.venv-mf/bin/mf"


@pytest.fixture
def gateway(tmp_path):
    from agent.gateway import Gateway

    mf = Path(os.getenv("CVM_TEST_MF", str(MF)))
    release_root = os.getenv("CVM_TEST_RELEASE_ROOT")
    if release_root:
        return Gateway(Path(release_root), mf, release_id=os.getenv("CVM_TEST_RELEASE_ID"))
    if not BASELINE.exists() or not mf.exists():
        pytest.skip("Set CVM_TEST_RELEASE_ROOT and CVM_TEST_MF to run pinned integration")
    (tmp_path / "environments/uat").mkdir(parents=True)
    (tmp_path / "environments/uat/current.json").write_text(
        json.dumps({"release_id": BASELINE.name})
    )
    (tmp_path / "snapshots").symlink_to(BASELINE.parent, target_is_directory=True)
    return Gateway(tmp_path, mf)


def intent(**overrides):
    from agent.contracts import QueryIntent

    return QueryIntent.model_validate({
        "action": "query",
        "metrics": ["reported_net_assets_eop", "net_flow"],
        "start_date": "2026-04-01",
        "end_date": "2026-04-30",
        "grain": "total",
        "dimensions": [],
        "filters": [],
        "presentation": "table",
        **overrides,
    })


@pytest.mark.parametrize("overrides", [
    {"where": "{{ dangerous() }}"},
    {"metrics": ["pl; drop table"]},
    {"dimensions": ["manager"]},
    {"start_date": "2026-4-01"},
    {"end_date": "2026-04-31"},
    {"filters": [{"field": "reporting_entity", "op": "eq", "values": [123]}]},
    {"filters": [{"field": "reporting_entity", "op": "eq", "values": ["a", "b"]}]},
])
def test_schema_rejects_malicious_or_invalid_intent(overrides):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        intent(**overrides)


def test_april_exact_partial_and_explain(gateway):
    from agent.render import render_result

    result = gateway.query_metrics(intent())
    assert result.status == "partial"
    row, = result.rows
    assert row.values["reported_net_assets_eop"] == Decimal("109568170483.04")
    assert row.values["net_flow"] == Decimal("1226480088.40")
    assert row.coverage["reported_net_assets_eop"].status == "complete"
    assert row.coverage["net_flow"].reported == 1196
    assert row.coverage["net_flow"].expected == 1200
    assert str(row.effective_cut) == "2026-04-30"
    assert "LIMIT 501" in gateway.explain_query(result.query_id)
    assert len(result.provenance.raw_result_sha256) == 64
    rendered = render_result(result)
    assert "1226480088.40" in rendered and "1196/1200" in rendered
    assert result.provenance.release_id in rendered


def test_real_partial_interval_uses_last_reporting_day(gateway):
    result = gateway.query_metrics(intent(start_date="2026-04-01", end_date="2026-04-05"))
    row, = result.rows
    assert str(row.effective_cut) == "2026-04-02"
    assert row.coverage["net_flow"].expected == 120


def test_full_interval_never_adds_stock(gateway):
    result = gateway.query_metrics(intent(end_date="2026-09-30"))
    row, = result.rows
    assert row.values["reported_net_assets_eop"] == Decimal("119385193058.06")
    assert row.values["net_flow"] == Decimal("4725910556.15")
    assert (row.coverage["net_flow"].reported, row.coverage["net_flow"].expected) == (7554, 7560)


def test_real_missing_class_does_not_backfill(gateway):
    import csv

    with (ROOT / "profiling/cvm/evidence/cohort.csv").open() as stream:
        entity = next(r["ID_Registro_Classe"] for r in csv.DictReader(stream)
                      if r["cnpj"] == "31963249000126")
    result = gateway.query_metrics(intent(
        start_date="2026-08-28", end_date="2026-08-28",
        filters=[{"field": "reporting_entity", "op": "eq", "values": [f"CVM:CLASS:{entity}"]}],
    ))
    row, = result.rows
    assert row.values["reported_net_assets_eop"] is None
    assert row.values["net_flow"] is None
    assert (row.coverage["net_flow"].reported, row.coverage["net_flow"].expected) == (0, 1)


def test_no_expected_days(gateway):
    result = gateway.query_metrics(intent(start_date="2026-04-03", end_date="2026-04-05"))
    assert result.status == "no_expected_observations"
    assert result.rows == ()


@pytest.mark.parametrize("override,code", [
    ({"start_date": "2026-03-31"}, "outside_snapshot"),
    ({"grain": "day", "end_date": "2026-09-30", "dimensions": ["reporting_entity"]}, "too_many_rows"),
    ({"dimensions": ["classification_at_capture", "reporting_entity"]}, "unsupported_capability"),
    ({"filters": [{"field": "classification_at_capture", "op": "eq",
                   "values": ["x' {{ dangerous() }} $(echo x)"]}]}, "invalid_plan"),
])
def test_invalid_requests_never_start_worker(gateway, monkeypatch, override, code):
    from agent.contracts import GatewayError

    def forbidden(*args, **kwargs):
        pytest.fail("invalid request started a worker")

    monkeypatch.setattr("agent.gateway.run_worker", forbidden)
    with pytest.raises(GatewayError) as caught:
        gateway.query_metrics(intent(**override))
    assert caught.value.code == code


def test_decimal_parser_distinguishes_missing_from_zero():
    from agent.results import parse_csv

    raw = b"metric_time__day,net_flow\n2026-04-01,\n2026-04-02,0.00\n"
    rows = parse_csv(raw, ("metric_time__day",), ("net_flow",))
    assert rows[("2026-04-01",)]["net_flow"] is None
    assert str(rows[("2026-04-02",)]["net_flow"]) == "0.00"


def test_result_overflow_rejected():
    from agent.contracts import GatewayError
    from agent.results import parse_csv

    raw = b"reporting_entity,net_flow\n" + b"".join(
        f"id{i},0.00\n".encode() for i in range(501)
    )
    with pytest.raises(GatewayError) as caught:
        parse_csv(raw, ("reporting_entity",), ("net_flow",))
    assert caught.value.code == "too_many_rows"


def test_worker_timeout_and_output_budget(tmp_path):
    import sys
    import time

    from agent.contracts import GatewayError
    from agent.worker import run_worker

    started = time.monotonic()
    with pytest.raises(GatewayError) as caught:
        run_worker([sys.executable, "-c", "import time; time.sleep(10)"], tmp_path, {},
                   timeout=0.1)
    assert caught.value.code == "timeout"
    assert time.monotonic() - started < 5
    with pytest.raises(GatewayError) as caught:
        run_worker([sys.executable, "-c", "print('x'*3000000)"], tmp_path, {}, timeout=5)
    assert caught.value.code == "tool_error"


def test_bundle_tampering_rejected_before_worker(tmp_path):
    from agent.contracts import GatewayError
    from agent.gateway import Gateway
    from release.snapshots import seal

    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "snapshot.duckdb").write_bytes(b"untampered")
    (candidate / "validation.json").write_text('{"passed": true}')
    root = tmp_path / "releases"
    pinned = seal(root, candidate, "example")
    (root / "environments/uat").mkdir(parents=True)
    (root / "environments/uat/current.json").write_text('{"release_id":"example"}')
    db = pinned / "snapshot.duckdb"
    db.chmod(0o644)
    db.write_bytes(b"tampered")
    with pytest.raises(GatewayError) as caught:
        Gateway(root, MF)
    assert caught.value.code == "snapshot_invalid"


def test_monthly_matches_independent_oracles(gateway):
    expected = json.loads((ROOT / "profiling/cvm/evidence/monthly-oracles.json").read_text())
    result = gateway.query_metrics(intent(end_date="2026-09-30", grain="month"))
    assert len(result.rows) == len(expected) == 6
    for row, oracle in zip(result.rows, expected, strict=True):
        assert row.group["metric_time__month"][:7] == oracle["period"]
        for metric in ("reported_net_assets_eop", "net_flow"):
            assert row.values[metric] == Decimal(oracle[metric])
        assert row.coverage["net_flow"].reported == oracle["observations"]
        assert row.coverage["reported_net_assets_eop"].expected == 60


def test_ratio_of_totals(gateway):
    result = gateway.query_metrics(intent(metrics=["reporting_coverage_period"]))
    row, = result.rows
    assert row.values["reporting_coverage_period"] == Decimal(1196) / Decimal(1200)


def test_category_membership_and_class_group(gateway):
    result = gateway.query_metrics(intent(
        metrics=["reported_net_assets_eop", "net_flow"], grain="day",
        start_date="2026-04-01", end_date="2026-04-01",
        dimensions=["reporting_entity"],
        filters=[{"field": "classification_at_capture", "op": "in",
                  "values": ["Ações", "Renda Fixa"]}],
    ))
    entities = {key for key, category in gateway._catalog.classes.items()
                if category in {"Ações", "Renda Fixa"}}
    assert {row.group["reporting_entity"] for row in result.rows} == entities
    assert all(row.coverage["net_flow"].expected == 1 for row in result.rows)


def test_pinned_gateway_never_rereads_pointer(gateway, monkeypatch):
    def missing(*args):
        pytest.fail("already-pinned gateway re-read the UAT pointer")

    monkeypatch.setattr("release.snapshots._state", missing)
    result = gateway.query_metrics(intent(
        start_date="2026-04-03", end_date="2026-04-05",
    ))
    assert result.provenance.release_id == gateway.get_catalog()["release_id"]


def test_only_approved_semantic_definition_is_accepted(gateway):
    from agent.catalog import Catalog

    manifest = json.loads(gateway._manifest)
    metric = next(m for m in manifest["metrics"] if m["name"] == "reported_net_assets_eop")
    metric["type_params"]["non_additive_dimension"] = None
    with pytest.raises(ValueError, match="Unreviewed semantic definition"):
        Catalog(json.dumps(manifest).encode(), {})


def test_actual_metricflow_adapter_denies_external_reads_and_writes(gateway, tmp_path):
    from shutil import copyfile

    from agent.worker import run_worker, scratch_project

    # Reuse the exact CLI configuration/adapter, on a disposable byte copy.
    # No user-controlled SQL enters the production API.
    probe = """
from dbt_metricflow.cli.cli_configuration import CLIConfiguration
cfg = CLIConfiguration()
cfg.setup()
assert cfg.sql_client.query('SELECT 1').rows[0][0] == 1
for sql, expected in (
    ('CREATE TABLE forbidden_agent_probe (id int)', 'read-only'),
    ("SELECT * FROM read_csv_auto('/etc/passwd')", 'disabled'),
    ("SELECT * FROM read_csv_auto('https://127.0.0.1/agent-probe.csv')", 'disabled'),
):
    try:
        cfg.sql_client.execute(sql)
    except Exception as exc:
        if expected not in str(exc).lower():
            raise
    else:
        raise AssertionError(sql)
print('hardening active')
"""
    database = tmp_path / gateway._db.name
    copyfile(gateway._db, database)
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    with scratch_project(database, gateway._manifest, gateway._dbt_project) as (project, env):
        python = str(gateway._mf.with_name("python"))
        assert run_worker([python, "-I", "-c", probe], project, env, timeout=30).strip() == b"hardening active"
    assert hashlib.sha256(database.read_bytes()).hexdigest() == digest


def test_terminal_controls_and_markup_escaped():
    from agent.render import _text

    assert _text("<b>\x1b[2J\n|&") == r"\u003cb\u003e\u001b[2J\u000a\u007c\u0026"


def test_timeout_kills_worker_descendants(tmp_path):
    import sys
    import time

    from agent.contracts import GatewayError
    from agent.worker import run_worker

    # A surviving descendant would create the marker after the parent timeout.
    marker = tmp_path / "orphan"
    child = f"import time; from pathlib import Path; time.sleep(0.8); Path({str(marker)!r}).touch()"
    ready = tmp_path / "ready"
    parent = (
        "import subprocess, sys, time; from pathlib import Path;"
        f"subprocess.Popen([sys.executable, '-c', {child!r}]);"
        f"Path({str(ready)!r}).touch();time.sleep(10)"
    )
    with pytest.raises(GatewayError) as caught:
        run_worker([sys.executable, "-c", parent], tmp_path, {}, timeout=0.5)
    assert caught.value.code == "timeout"
    assert ready.is_file()
    time.sleep(0.8)
    assert not marker.exists()


def test_explain_and_query_use_same_worker_arguments(gateway, monkeypatch):
    import agent.gateway as module

    run = module.run_worker
    invocations = []

    def observe(argv, cwd, env, **kwargs):
        invocations.append((list(argv), cwd, (cwd / "target/semantic_manifest.json").read_bytes()))
        return run(argv, cwd, env, **kwargs)

    monkeypatch.setattr(module, "run_worker", observe)
    result = gateway.query_metrics(intent(metrics=["net_flow"], start_date="2026-04-29"))
    explain, execute = invocations
    assert [arg for arg in explain[0] if arg != "--explain"] == execute[0]
    assert str(gateway._mf) in execute[0]
    assert explain[1:] == execute[1:]
    assert hashlib.sha256(execute[2]).hexdigest() == result.provenance.semantic_manifest_sha256
    assert hashlib.sha256(gateway.explain_query(result.query_id).encode()).hexdigest() == (
        result.provenance.compiled_sql_sha256
    )


def test_fixed_entry_blocks_python_network(tmp_path):
    import sys

    from agent.worker import ENTRY, run_worker

    probe = tmp_path / "probe.py"
    probe.write_text(
        "import socket\n"
        "try:\n"
        "    socket.socket()\n"
        "except PermissionError:\n"
        "    print('network denied')\n"
        "else:\n"
        "    raise AssertionError('network permitted')\n"
    )
    # The wrapper is run inside the installed MetricFlow environment, as in
    # production. Use a controlled entry only to try a socket directly.
    if not MF.exists() and not os.getenv("CVM_TEST_MF"):
        pytest.skip("MetricFlow environment required")
    mf = Path(os.getenv("CVM_TEST_MF", str(MF)))
    python = str(mf.with_name("python"))
    assert run_worker([python, "-I", str(ENTRY), str(probe)], tmp_path, {
        "HOME": str(tmp_path), "TMPDIR": str(tmp_path),
    }, timeout=5).strip() == b"network denied"


def test_rejects_chart_even_with_valid_table_data(gateway):
    from agent.contracts import GatewayError

    with pytest.raises(GatewayError) as caught:
        gateway.query_metrics(intent(presentation="chart"))
    assert caught.value.code == "unsupported_capability"


def test_actual_executed_sql_mismatch_blocks_answer(gateway, monkeypatch):
    import agent.gateway as module
    from agent.contracts import GatewayError

    run = module.run_worker

    def mismatch(argv, *args, **kwargs):
        result = run(argv, *args, **kwargs)
        return result if "--explain" in argv else b"SELECT 0"

    monkeypatch.setattr(module, "run_worker", mismatch)
    with pytest.raises(GatewayError) as caught:
        gateway.query_metrics(intent(metrics=["net_flow"]))
    assert caught.value.code == "result_invalid"
