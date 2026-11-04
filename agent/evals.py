"""Score live planner decisions against a frozen split, with separate numeric oracles."""
import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from importlib.metadata import version
from pathlib import Path

from agent.auth import AuthError, CredentialStore
from agent.catalog import METRICS, POLICY, canonical, sha256
from agent.cli import DECISION, add_gateway_options, configure_terminal, configured_gateway
from agent.contracts import Coverage, Decision, GatewayError, QueryIntent, QueryResult, ResultRow
from agent.planner import (
    BACKEND, INSTRUCTIONS, MODEL, SETTINGS, TURN_SECONDS, PlannerError, codex_model, plan, planner_code_sha256,
    run_decision,
)

DATASET = Path(__file__).parent / "evaluation/v1"
ORACLE_SHA256 = "c09c94327d3b7334a1838acc1f0345f0232190cce57135c942cf6b25b68616b7"
ORACLE_SOURCE_FINGERPRINT = "7c9da2695979f443972795e6ae4eea3932fc855ef60d3d07a4a5924c2b97bb58"
FROZEN_SHA256 = {
    "development": "02ce841b61fc5494cf28e19d3af4ddbdf96b6acfef6e24212cc221661f0b7b72",
    "holdout": "b149481662e810cc1e33566ca002fb74947e10242bb063e77c6426aec1c26337",
}


@dataclass(frozen=True)
class Case:
    id: str
    family: str
    question: str
    reference_date: date
    critical: bool
    expected: tuple[Decision, ...]
    oracle: dict | None


def load_cases(split: str) -> tuple[list[Case], str]:
    digest = FROZEN_SHA256[split]
    data = (DATASET / f"{split}.json").read_bytes()
    if sha256(data) != digest:
        raise PlannerError("eval_dataset_changed")
    payload = json.loads(data)
    if (payload["version"], payload["split"], payload["policy"], payload["timezone"]) != (
        "1", split, POLICY, "America/Sao_Paulo",
    ):
        raise PlannerError("eval_dataset_invalid")
    clock = date.fromisoformat(payload["reference_date"])
    oracle_data = (DATASET / "oracles.json").read_bytes()
    if sha256(oracle_data) != ORACLE_SHA256:
        raise PlannerError("eval_oracles_changed")
    oracles = json.loads(oracle_data)
    cases = []
    for row in payload["families"]:
        family = row["family"]
        accepted = tuple(DECISION.validate_python(item) for item in row["expected"])
        queries = [item for item in accepted if isinstance(item, QueryIntent)]
        oracle = oracles.get(family)
        if bool(queries) != (oracle is not None) or len(queries) > 1:
            raise PlannerError("eval_oracle_missing_or_ambiguous")
        if oracle is not None:
            try:
                _oracle_rows(queries[0], oracle)
            except (KeyError, TypeError, ValueError, InvalidOperation):
                raise PlannerError("eval_oracle_invalid") from None
        cases.extend(
            Case(f"{family}-{language}", family, question, clock, row["critical"], accepted, oracle)
            for language, question in row["questions"].items()
        )
    return cases, digest


def normalized(decision: Decision) -> bytes:
    data = decision.model_dump(mode="json")
    if isinstance(decision, QueryIntent):
        data["metrics"].sort()
        data["dimensions"].sort()
        for condition in data["filters"]:
            condition["values"].sort()
        data["filters"].sort(key=canonical)
    for key in ("missing_slots", "alternatives"):
        if key in data:
            data[key].sort()
    return canonical(data)


def _oracle_rows(intent: QueryIntent, oracle: dict) -> dict[bytes, ResultRow]:
    if set(oracle) != {"status", "rows"} or not isinstance(oracle["rows"], list):
        raise ValueError("Invalid oracle envelope")
    group_keys = set(intent.dimensions)
    if intent.grain != "total":
        group_keys.add(f"metric_time__{intent.grain}")
    metrics = set(intent.metrics)
    expected = {}
    for row in oracle["rows"]:
        if set(row) != {"group", "effective_cut", "values", "counts", "supporting_counts"}:
            raise ValueError("Invalid oracle row shape")
        if set(row["group"]) != group_keys or set(row["values"]) != metrics or set(row["counts"]) != metrics:
            raise ValueError("Incomplete oracle row")
        cut = date.fromisoformat(row["effective_cut"])
        if not intent.start_date <= cut.isoformat() <= intent.end_date:
            raise ValueError("Oracle cut outside intent")
        group = canonical(row["group"])
        if group in expected:
            raise ValueError("Duplicate oracle row")
        values = {}
        coverage = {}
        supporting_counts = {}
        for metric in intent.metrics:
            reported, count = row["counts"][metric]
            if type(reported) is not int or type(count) is not int or not 0 <= reported <= count or not count:
                raise ValueError("Invalid oracle coverage")
            coverage[metric] = Coverage(
                reported=reported, expected=count, status="complete" if reported == count else "partial",
            )
            for key, value in zip(METRICS[metric][3], (reported, count), strict=True):
                if supporting_counts.setdefault(key, value) != value:
                    raise ValueError("Conflicting oracle counts")
            amount = row["values"][metric]
            if amount is not None and not isinstance(amount, str):
                raise ValueError("Use decimal strings for numeric oracles")
            value = Decimal(amount) if amount is not None else None
            if value is not None and not value.is_finite():
                raise ValueError("Nonfinite oracle value")
            if METRICS[metric][0] == "BRL":
                if (value is None) != (reported == 0) or (value is not None and value.as_tuple().exponent < -2):
                    raise ValueError("Invalid money oracle")
            elif value is None or not 0 <= value <= 1:
                raise ValueError("Invalid ratio oracle")
            values[metric] = value
        if row["supporting_counts"] != supporting_counts or any(
            type(value) is not int for value in row["supporting_counts"].values()
        ):
            raise ValueError("Incomplete supporting counts")
        expected[group] = ResultRow(group=row["group"], effective_cut=cut, values=values, coverage=coverage,
                                    supporting_counts=supporting_counts)
    if expected:
        partial = any(coverage.status == "partial" for row in expected.values() for coverage in row.coverage.values())
        if oracle["status"] != ("partial" if partial else "ok"):
            raise ValueError("Invalid oracle status")
    elif oracle["status"] not in {"empty", "no_expected_observations"}:
        raise ValueError("Invalid empty oracle status")
    return expected


def oracle_matches(result: QueryResult, oracle: dict) -> bool:
    try:
        expected = _oracle_rows(result.intent, oracle)
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False
    if result.status != oracle["status"] or len(result.rows) != len(expected):
        return False
    for row in result.rows:
        target = expected.pop(canonical(row.group), None)
        if (target is None or row.effective_cut != target.effective_cut or row.coverage != target.coverage
                or row.supporting_counts != target.supporting_counts or row.values.keys() != target.values.keys()):
            return False
        for metric, value in row.values.items():
            golden = target.values[metric]
            if value is not None and not value.is_finite():
                return False
            if value is None or golden is None or METRICS[metric][0] == "BRL":
                if value != golden:
                    return False
            elif abs(value - golden) > Decimal("0.000000000001"):
                return False
    return True


def summarize(rows: list[dict]) -> dict:
    def score(selected: list[dict], field: str) -> dict:
        return {"passed": sum(row[field] for row in selected), "trials": len(selected)}

    return {
        "exact": score(rows, "exact"),
        "supported": score([row for row in rows if row["supported"]], "exact"),
        "critical": score([row for row in rows if row["critical"]], "exact"),
        "numeric_oracle": score([row for row in rows if "oracle_exact" in row], "oracle_exact"),
    }


async def evaluate(model, gateway, cases: list[Case], *, repeats: int, execute: bool) -> list[dict]:
    catalog = gateway.get_catalog()
    rows = []
    for repetition in range(1, repeats + 1):
        for case in cases:
            start = time.monotonic()
            deadline = start + TURN_SECONDS
            row = {"case": case.id, "repetition": repetition, "critical": case.critical,
                   "supported": any(isinstance(item, QueryIntent) for item in case.expected), "exact": False}
            if execute and case.oracle is not None:
                row["oracle_exact"] = False
            try:
                planned = await plan(model, case.question, catalog, deadline=deadline, reference_date=case.reference_date,
                                     validate_intent=gateway.validate_intent)
                decision = normalized(planned.decision)
                row.update(
                    exact=any(decision == normalized(item) for item in case.expected),
                    action=planned.decision.action, decision=json.loads(decision), **planned.trace(),
                )
                if execute and row["exact"] and isinstance(planned.decision, QueryIntent):
                    result = run_decision(gateway, planned.decision, deadline=deadline)
                    row.update(gateway_status=result.status, query_sha256=result.query_hash,
                               provenance=result.provenance.model_dump(mode="json"))
                    if case.oracle is not None:
                        row["oracle_exact"] = oracle_matches(result, case.oracle)
            except PlannerError as exc:
                row.update(failure=str(exc), **exc.trace)
            except GatewayError as exc:
                row["gateway_failure"] = exc.code
            row["elapsed_ms"] = int((time.monotonic() - start) * 1000)
            rows.append(row)
    return rows


async def _run(args, cases, dataset_hash) -> dict:
    gateway = configured_gateway(args)
    identity = gateway.get_identity()
    if args.execute and identity["source_fingerprint"] != ORACLE_SOURCE_FINGERPRINT:
        raise PlannerError("eval_oracle_source_mismatch")
    catalog_hash = sha256(canonical(gateway.get_catalog()))
    async with codex_model(CredentialStore()) as model:
        rows = await evaluate(model, gateway, cases, repeats=args.repeats, execute=args.execute)
    summary = summarize(rows)
    families = sorted({case.family for case in cases})
    return {
        "mode": "experimental live model evaluation", "dataset_version": "1",
        "dataset_sha256": dataset_hash, "oracle_sha256": ORACLE_SHA256, "split": args.split,
        "requested_model": MODEL, "backend": BACKEND,
        "planner_code_sha256": planner_code_sha256(), "runner_code_sha256": sha256(Path(__file__).read_bytes()),
        "instructions_sha256": sha256(INSTRUCTIONS.encode()),
        "runtime_versions": {name: version(name) for name in ("pydantic-ai-slim", "openai", "httpx2")},
        "settings": SETTINGS, "verified_identity": identity, "catalog_sha256": catalog_hash, "summary": summary,
        "families": {family: summarize([row for row in rows if row["case"].startswith(f"{family}-")])
                     for family in families},
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_gateway_options(parser)
    parser.add_argument("--split", choices=tuple(FROZEN_SHA256), default="development")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--repeats", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--execute", action="store_true", help="Execute exact query decisions and score available oracles")
    parser.add_argument("--authorize-expanded", action="store_true",
                        help="Confirm prior review before spending credits on holdout or more than three trials")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be positive")
    if (args.split == "holdout" or args.limit * args.repeats > 3) and not args.authorize_expanded:
        parser.error("expanded and holdout runs require --authorize-expanded after review")
    configure_terminal()
    try:
        cases, digest = load_cases(args.split)
        print(json.dumps(asyncio.run(_run(args, cases[:args.limit], digest)), sort_keys=True))
    except GatewayError as exc:
        print(exc.code, file=sys.stderr)
        return 1
    except (AuthError, PlannerError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("eval_error", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
