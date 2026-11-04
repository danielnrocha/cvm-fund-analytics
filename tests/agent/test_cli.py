import json

from agent.cli import main


def test_plan_file_never_requires_oauth(tmp_path, capsys):
    plan = tmp_path / "intent.json"
    plan.write_text(json.dumps({"action": "clarify", "reason": "missing_period", "missing_slots": ["period"]}))
    assert main(["plan-file", str(plan)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Mode: deterministic plan file", "Clarification needed: missing_period (period)",
    ]


def test_invalid_plan_file_does_not_echo_input(tmp_path, capsys):
    plan = tmp_path / "intent.json"
    plan.write_text('{"action":"secrets"}')
    assert main(["plan-file", str(plan)]) == 1
    assert capsys.readouterr().err.strip() == "invalid_plan"


def test_explain_reads_only_the_query_result_already_executed(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    from agent import cli

    path = tmp_path / "query.json"
    path.write_text(json.dumps({
        "action": "query", "metrics": ["net_flow"], "start_date": "2026-04-01",
        "end_date": "2026-04-30", "grain": "total", "dimensions": [], "filters": [],
        "presentation": "table",
    }))
    calls = []

    class FakeGateway:
        def query_metrics(self, decision, *, deadline):
            calls.append(("query", decision.action))
            return SimpleNamespace(query_id="abc", provenance=SimpleNamespace(compiled_sql_sha256="hash"))

        def explain_query(self, query_id):
            calls.append(("explain", query_id))
            return "SELECT approved_sql"

    monkeypatch.setattr(cli, "configured_gateway", lambda args: FakeGateway())
    monkeypatch.setattr(cli, "render_outcome", lambda outcome: "result")
    assert main(["plan-file", str(path), "--explain"]) == 0
    assert calls == [("query", "query"), ("explain", "abc")]
    assert "SELECT approved_sql" in capsys.readouterr().out
