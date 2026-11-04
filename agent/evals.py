"""Score live planner decisions against a frozen split, with separate numeric oracles."""
import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from agent.auth import AuthError, CredentialStore
from agent.catalog import POLICY, canonical, sha256
from agent.cli import DECISION, add_gateway_options, configured_gateway
from agent.contracts import Decision, GatewayError, QueryIntent, QueryResult
from agent.planner import BACKEND, MODEL, SETTINGS, TURN_SECONDS, PlannerError, codex_model, plan, run_decision

DATASET = Path(__file__).parent / "evaluation/v1"
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
    cases = [
        Case(f"{row['family']}-{language}", row["family"], question, clock, row["critical"],
             tuple(DECISION.validate_python(item) for item in row["expected"]), row["oracle"])
        for row in payload["families"]
        for language, question in row["questions"].items()
    ]
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


def oracle_matches(result: QueryResult, oracle: dict) -> bool:
    if result.status != oracle["status"] or len(result.rows) != oracle["row_count"]:
        return False
    if not result.rows:
        return True
    row = result.rows[0]
    return (
        row.effective_cut.isoformat() == oracle["effective_cut"]
        and all(row.values[metric] == (None if value is None else Decimal(value))
                for metric, value in oracle.get("values", {}).items())
        and all([row.coverage[metric].reported, row.coverage[metric].expected] == counts
                for metric, counts in oracle.get("counts", {}).items())
    )


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
                planned = await plan(model, case.question, catalog, deadline=deadline, reference_date=case.reference_date)
                decision = normalized(planned.decision)
                row.update(
                    exact=any(decision == normalized(item) for item in case.expected),
                    action=planned.decision.action, attempts=planned.attempts,
                    prompt_sha256=planned.prompt_sha256, schema_sha256=planned.schema_sha256,
                    catalog_sha256=planned.catalog_sha256, decision_sha256=planned.decision_sha256,
                )
                if execute and row["exact"] and isinstance(planned.decision, QueryIntent):
                    result = run_decision(gateway, planned.decision, deadline=deadline)
                    row.update(gateway_status=result.status, query_sha256=result.query_hash,
                               provenance=result.provenance.model_dump(mode="json"))
                    if case.oracle is not None:
                        row["oracle_exact"] = oracle_matches(result, case.oracle)
            except PlannerError as exc:
                row["failure"] = str(exc)
            except GatewayError as exc:
                row["gateway_failure"] = exc.code
            row["elapsed_ms"] = int((time.monotonic() - start) * 1000)
            rows.append(row)
    return rows


async def _run(args, cases, dataset_hash) -> dict:
    gateway = configured_gateway(args)
    async with codex_model(CredentialStore()) as model:
        rows = await evaluate(model, gateway, cases, repeats=args.repeats, execute=args.execute)
    summary = summarize(rows)
    families = sorted({case.family for case in cases})
    return {
        "mode": "experimental live model evaluation", "dataset_version": "1",
        "dataset_sha256": dataset_hash, "split": args.split, "model": MODEL, "backend": BACKEND,
        "pydantic_ai_version": version("pydantic-ai-slim"), "settings": SETTINGS,
        "release_id": gateway.get_catalog()["release_id"], "summary": summary,
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
    logging.disable(logging.CRITICAL)
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
