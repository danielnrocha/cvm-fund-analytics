"""Run the single-turn CVM planner or execute an operator-supplied intent."""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import pydantic_ai
from pydantic import TypeAdapter, ValidationError

from agent.auth import AuthError, CredentialStore
from agent.catalog import canonical, sha256
from agent.contracts import ClarifyIntent, Decision, GatewayError, QueryIntent, UnsupportedIntent
from agent.gateway import Gateway
from agent.planner import (
    BACKEND, MODEL, OUTPUT_BYTES, TURN_SECONDS, PlannerError, codex_model, plan, planner_code_sha256, run_decision,
)
from agent.render import render_result

DECISION = TypeAdapter(Decision)


def add_gateway_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--release-id")
    parser.add_argument("--mf", type=Path)


def configured_gateway(args: argparse.Namespace) -> Gateway:
    if args.release_root is None or args.mf is None:
        raise PlannerError("gateway_configuration_required")
    return Gateway(args.release_root, args.mf.resolve(), release_id=args.release_id)


def _print_result(gateway, decision: Decision, *, deadline: float, explain: bool) -> None:
    outcome = run_decision(gateway, decision, deadline=deadline)
    print(render_outcome(outcome))
    if explain and isinstance(decision, QueryIntent) and outcome.provenance.compiled_sql_sha256:
        print("Executed SQL")
        print(gateway.explain_query(outcome.query_id))


def render_outcome(outcome) -> str:
    if isinstance(outcome, ClarifyIntent):
        return f"Clarification needed: {outcome.reason} ({', '.join(outcome.missing_slots)})"
    if isinstance(outcome, UnsupportedIntent):
        suffix = " Try " + ", ".join(outcome.alternatives) + "." if outcome.alternatives else ""
        return f"Unsupported: {outcome.reason}.{suffix}"
    return render_result(outcome)


async def _ask(args, store: CredentialStore, gateway: Gateway, deadline: float) -> None:
    async with codex_model(store) as model:
        result = await plan(model, args.question, gateway.get_catalog(), deadline=deadline)
    print(f"Mode: experimental Codex OAuth ({MODEL})")
    trace = {"requested_model": MODEL, "planner_code_sha256": planner_code_sha256(),
             "elapsed_ms": int((time.monotonic() - (deadline - TURN_SECONDS)) * 1000), **result.trace()}
    print("Planner trace: " + json.dumps(trace, sort_keys=True))
    if args.plan_only:
        print(json.dumps(result.decision.model_dump(mode="json"), ensure_ascii=True, sort_keys=True))
    else:
        _print_result(gateway, result.decision, deadline=deadline, explain=args.explain)


def configure_terminal() -> None:
    logging.disable(logging.CRITICAL)
    pydantic_ai.BANNER_ENABLED = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_gateway_options(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    ask = commands.add_parser("ask", help="Experimental natural-language planner")
    ask.add_argument("question")
    display = ask.add_mutually_exclusive_group()
    display.add_argument("--plan-only", action="store_true", help="Display the structured decision without executing it")
    display.add_argument("--explain", action="store_true", help="Print the verified executed SQL for a query")
    plan_file = commands.add_parser("plan-file", help="Execute a deterministic JSON Decision")
    plan_file.add_argument("path", type=Path)
    plan_file.add_argument("--explain", action="store_true", help="Print the verified executed SQL for a query")
    commands.add_parser("health", help="Inspect the credential file and optionally verify a gateway release")
    args = parser.parse_args(argv)
    configure_terminal()
    store = CredentialStore()
    deadline = time.monotonic() + TURN_SECONDS
    try:
        if args.command == "health":
            data = {"backend": BACKEND, "model": MODEL, "auth": store.status(), "gateway": "unconfigured"}
            if any((args.release_root, args.release_id, args.mf)):
                catalog = configured_gateway(args).get_catalog()
                data.update(gateway="verified", release_id=catalog["release_id"],
                            semantic_manifest_sha256=catalog["semantic_manifest_sha256"],
                            catalog_sha256=sha256(canonical(catalog)))
            print(json.dumps(data, sort_keys=True))
        elif args.command == "ask":
            asyncio.run(_ask(args, store, configured_gateway(args), deadline))
        else:
            with args.path.open("rb") as stream:
                data = stream.read(OUTPUT_BYTES + 1)
            if len(data) > OUTPUT_BYTES:
                raise PlannerError("invalid_plan")
            decision = DECISION.validate_json(data)
            gateway = configured_gateway(args) if isinstance(decision, QueryIntent) else None
            print("Mode: deterministic plan file")
            _print_result(gateway, decision, deadline=deadline, explain=args.explain)
    except GatewayError as exc:
        print(exc.code, file=sys.stderr)
        return 1
    except (AuthError, PlannerError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, ValidationError):
        print("invalid_plan" if args.command == "plan-file" else "agent_error", file=sys.stderr)
        return 1
    except Exception:
        print("agent_error", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
