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
