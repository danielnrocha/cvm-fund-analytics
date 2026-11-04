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
def mf_executable():
    return Path(os.getenv("CVM_TEST_MF", str(MF)))


@pytest.fixture
def gateway(tmp_path, mf_executable):
    from agent.gateway import Gateway

    mf = mf_executable
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


def test_bundle_tampering_rejected_before_worker(tmp_path, mf_executable):
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
        Gateway(root, mf_executable)
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


def test_fixed_entry_blocks_python_network(tmp_path, mf_executable):
    import sys

    from agent.worker import run_worker

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
    if not mf_executable.exists():
        pytest.skip("MetricFlow environment required")
    python = str(mf_executable.with_name("python"))
    entry = ROOT / "agent/_mf_entry.py"
    assert run_worker([python, "-I", str(entry), str(probe)], tmp_path, {
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


def test_clipped_monthly_bounds_preserve_exact_coverage_and_closing_values(gateway):
    # Independent direct aggregate of frozen fct_daily on the requested dates,
    # using the last report_date per month as the closing cut.
    expected = (
        ("2026-04-01", "2026-04-30", "109568170483.04", "1068725316.01", 1137, 1140),
        ("2026-05-01", "2026-05-29", "110473691592.44", "-308203062.21", 1199, 1200),
        ("2026-06-01", "2026-06-02", "110716879089.14", "117438309.55", 120, 120),
    )
    result = gateway.query_metrics(intent(grain="month", start_date="2026-04-02",
                                          end_date="2026-06-02"))
    for row, oracle in zip(result.rows, expected, strict=True):
        month, cut, pl, flow, reported, expected_count = oracle
        assert row.group == {"metric_time__month": month}
        assert row.effective_cut.isoformat() == cut
        assert row.values == {"reported_net_assets_eop": Decimal(pl), "net_flow": Decimal(flow)}
        assert row.supporting_counts == {
            "reporting_entities_eop": 60, "expected_entities_eop": 60,
            "reporting_observations": reported, "expected_observations": expected_count,
        }


def test_wrapper_edit_after_startup_does_not_change_executed_code(gateway, tmp_path, monkeypatch):
    import agent.gateway as gateway_module
    import agent.worker as worker_module

    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for name in gateway_module._GATEWAY_FILES:
        (checkout / name).write_bytes((ROOT / "agent" / name).read_bytes())
    entry = checkout / "_mf_entry.py"
    original = entry.read_bytes()
    monkeypatch.setattr(gateway_module, "__file__", str(checkout / "gateway.py"))
    monkeypatch.setattr(worker_module, "ENTRY", entry, raising=False)
    session = gateway_module.Gateway(gateway._db.parents[2], gateway._mf,
                                     release_id=gateway._release_id)
    entry.write_text("raise RuntimeError('wrapper changed after startup')\n")
    run_worker = gateway_module.run_worker

    def observe(argv, cwd, *args, **kwargs):
        staged_entry = Path(argv[2])
        assert staged_entry.parent == cwd
        assert staged_entry.read_bytes() == original
        return run_worker(argv, cwd, *args, **kwargs)

    monkeypatch.setattr(gateway_module, "run_worker", observe)
    result = session.query_metrics(intent(metrics=["net_flow"]))
    assert result.rows[0].values["net_flow"] == Decimal("1226480088.40")
    assert result.provenance.gateway_code_sha256 == gateway._code_hash
    assert result.provenance.source_revision is None


@pytest.mark.parametrize("has_rows", [True, False])
def test_host_rejects_result_when_final_work_crosses_deadline(gateway, monkeypatch, has_rows):
    from types import SimpleNamespace

    import agent.gateway as module
    from agent.contracts import GatewayError

    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock.now))
    if has_rows:
        query = gateway._query_pair
        validate = module.checked_rows

        def nearly_late(*args):
            result = query(*args)
            clock.now = 59.0
            return result

        def late_validation(*args):
            rows = validate(*args)
            clock.now = 61.0
            return rows

        monkeypatch.setattr(gateway, "_query_pair", nearly_late)
        monkeypatch.setattr(module, "checked_rows", late_validation)
        request = intent(metrics=["net_flow"])
    else:
        verify = gateway._check_db

        def late_check(*args):
            verify(*args)
            clock.now = 61.0

        monkeypatch.setattr(gateway, "_check_db", late_check)
        request = intent(start_date="2026-04-03", end_date="2026-04-05")

    with pytest.raises(GatewayError) as caught:
        gateway.query_metrics(request)
    assert caught.value.code == "timeout"
    assert gateway._explanations == {}


def test_expired_host_deadline_rejects_before_worker(gateway, monkeypatch):
    import time

    from agent.contracts import GatewayError

    def forbidden(*_args, **_kwargs):
        pytest.fail("an expired deadline started a worker")

    monkeypatch.setattr("agent.gateway.run_worker", forbidden)
    with pytest.raises(GatewayError) as caught:
        gateway.query_metrics(intent(), deadline=time.monotonic() - 1)
    assert caught.value.code == "timeout"


def test_plan_policy_checks_without_invoking_worker(gateway, monkeypatch):
    from agent.contracts import GatewayError

    def forbidden(*args, **kwargs):
        pytest.fail("planning started MetricFlow")

    monkeypatch.setattr(gateway, "_query_pair", forbidden)
    gateway.validate_intent(intent())
    for invalid in (intent(presentation="chart"), intent(start_date="2026-01-01"),
                    intent(filters=[{"field": "reporting_entity", "op": "eq", "values": ["unknown"]}])):
        with pytest.raises(GatewayError):
            gateway.validate_intent(invalid)
    identity = gateway.get_identity()
    assert len(identity["bundle_sha256"]) == len(identity["gateway_code_sha256"]) == 64
    assert identity["semantic_manifest_sha256"] == gateway.get_catalog()["semantic_manifest_sha256"]


def test_synthetic_result_preserves_cents_null_zero_and_unequal_denominators():
    from datetime import date

    from agent.results import checked_rows, parse_csv

    query = intent(
        metrics=["reported_net_assets_eop", "net_flow", "reporting_coverage_period"],
        end_date="2026-05-31",
        grain="month",
    )
    metrics = tuple(query.metrics) + (
        "reporting_entities_eop", "expected_entities_eop",
        "reporting_observations", "expected_observations",
    )
    months = {
        "2026-04-01": (date(2026, 4, 29), date(2026, 4, 30)),
        "2026-05-01": tuple(date(2026, 5, day) for day in range(4, 8)),
    }
    raw = (
        ("metric_time__month," + ",".join(metrics) + "\n").encode()
        + b"2026-04-01,,17.36,0.25,0,2,1,4\n"
        + b"2026-05-01,0.00,-9007199254740993.21,0.875,2,2,7,8\n"
    )
    first, second = checked_rows(
        parse_csv(raw, ("metric_time__month",), metrics),
        query, ("class-a", "class-b"), months, metrics,
    )
    assert first.values == {
        "reported_net_assets_eop": None,
        "net_flow": Decimal("17.36"),
        "reporting_coverage_period": Decimal("0.25"),
    }
    assert second.values == {
        "reported_net_assets_eop": Decimal("0.00"),
        "net_flow": Decimal("-9007199254740993.21"),
        "reporting_coverage_period": Decimal("0.875"),
    }
    for row, cut, reported, expected in (
        (first, date(2026, 4, 30), 1, 4),
        (second, date(2026, 5, 7), 7, 8),
    ):
        assert row.effective_cut == cut
        coverage = row.coverage["reporting_coverage_period"]
        assert (coverage.reported, coverage.expected, coverage.status) == (reported, expected, "partial")
