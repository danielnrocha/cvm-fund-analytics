from collections import Counter

from agent.evals import load_cases, summarize


def test_versioned_dataset_has_disjoint_families_and_three_variants():
    development, dev_hash = load_cases("development")
    holdout, holdout_hash = load_cases("holdout")
    assert len(development) == 72
    assert len(holdout) == 48
    assert not {case.family for case in development} & {case.family for case in holdout}
    assert set(Counter(case.family for case in development + holdout).values()) == {3}
    assert dev_hash != holdout_hash
    from agent.contracts import QueryIntent
    all_cases = development + holdout
    assert sum(case.oracle is not None for case in all_cases) == 54
    assert all((case.oracle is not None) == any(isinstance(item, QueryIntent) for item in case.expected)
               for case in all_cases)


def test_summary_does_not_count_unrun_oracles_as_successes():
    result = summarize([
        {"exact": True, "supported": True, "critical": True, "oracle_exact": True},
        {"exact": False, "supported": True, "critical": True},
        {"exact": True, "supported": False, "critical": False},
    ])
    assert result == {
        "exact": {"passed": 2, "trials": 3},
        "supported": {"passed": 1, "trials": 2},
        "critical": {"passed": 1, "trials": 2},
        "numeric_oracle": {"passed": 1, "trials": 1},
    }


def test_oracle_compares_all_rows_and_exact_keys():
    from datetime import date
    from decimal import Decimal
    from types import SimpleNamespace

    from agent.contracts import Coverage, QueryIntent, ResultRow
    from agent.evals import oracle_matches

    intent = QueryIntent(action="query", metrics=["net_flow"], start_date="2026-04-01", end_date="2026-05-31",
                         grain="month", dimensions=[], filters=[], presentation="table")

    def expected(month, cut, amount):
        return {"group": {"metric_time__month": f"2026-{month}-01"}, "effective_cut": f"2026-{month}-{cut}",
                "values": {"net_flow": amount}, "counts": {"net_flow": [3, 4]},
                "supporting_counts": {"reporting_observations": 3, "expected_observations": 4}}

    first = expected("04", "30", "12.50")
    second = expected("05", "29", "12.60")
    rows = tuple(ResultRow(group=row["group"], effective_cut=date.fromisoformat(row["effective_cut"]),
                           values={"net_flow": Decimal(row["values"]["net_flow"])},
                           coverage={"net_flow": Coverage(reported=3, expected=4, status="partial")},
                           supporting_counts=row["supporting_counts"]) for row in (first, second))
    result = SimpleNamespace(intent=intent, status="partial", rows=rows)
    oracle = {"status": "partial", "rows": [first, second]}
    assert oracle_matches(result, oracle)
    assert not oracle_matches(result, {"status": "partial", "rows": [first]})
    assert not oracle_matches(result, {"status": "partial", "rows": [first, dict(second, values={})]})
    assert not oracle_matches(result, {"status": "partial", "rows": [first, dict(second, counts={})]})
    assert not oracle_matches(result, {"status": "partial", "rows": [first, dict(second, supporting_counts={})]})
    assert not oracle_matches(result, {"status": "partial", "rows": [first, dict(second, values={"net_flow": "12.61"})]})


def test_failed_evaluation_keeps_runtime_and_attempt_evidence(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager
    from datetime import date
    from types import SimpleNamespace

    from pydantic_ai.messages import ModelResponse, TextPart
    from pydantic_ai.models.function import FunctionModel

    from agent import evals
    from agent.contracts import ClarifyIntent

    class Gateway:
        def get_identity(self):
            return {"release_id": "verified", "bundle_sha256": "bundle", "semantic_manifest_sha256": "manifest"}

        def get_catalog(self):
            return {"release_id": "verified"}

        def validate_intent(self, intent):
            raise AssertionError("Unexpected query")

    def model(messages, info):
        return ModelResponse(parts=[TextPart("untrusted model payload")])

    @asynccontextmanager
    async def provider(store):
        yield FunctionModel(model)

    monkeypatch.setattr(evals, "configured_gateway", lambda args: Gateway())
    monkeypatch.setattr(evals, "codex_model", provider)
    expected = ClarifyIntent(action="clarify", reason="missing_period", missing_slots=["period"])
    cases = [evals.Case("D1-pt", "D1", "PL", date(2026, 11, 15), True, (expected,), None)]
    report = asyncio.run(evals._run(SimpleNamespace(repeats=1, execute=False, split="development"), cases, "data"))
    assert report["verified_identity"]["bundle_sha256"] == "bundle"
    assert report["verified_identity"]["semantic_manifest_sha256"] == "manifest"
    row, = report["rows"]
    assert row["failure"] == "invalid_model_output"
    assert row["model_requests"] == 2
    assert len(row["attempt_trace"]) == 2
    assert "untrusted model payload" not in str(report)
