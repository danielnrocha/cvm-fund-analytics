# Wizard implementation qualification — no model downloads

> **Superseded 2026-11-04:** the user rejected trial-dependent Wizard access. Do not execute account/signup/trial instructions below. They are historical research only. Follow [the local implementation plan](local-agent-implementation-plan.md) and retain W01–W12 as technical test cases.

Date: 2026-10-28. Status: **proposed next step; not executed**. Implementation source baseline: main `c884ebcf4d16095aa5c48776b20a6f196ae2b7d0` (PR #3). [Post-merge acceptance](https://github.com/danielnrocha/cvm-fund-analytics/actions/runs/40802646918) passed on Linux ARM64. This document scopes a compatibility spike, not the complete analytics agent.

## Decision

Prefer Wizard as the coding assistant in the VS Code integrated terminal alongside the official dbt extension. Use Pydantic AI with deterministic test-model responses, then execute actual MetricFlow queries against an immutable snapshot. Do not install Ollama, download weights, invoke a real analytics LLM, activate billing, add payment details or configure paid provider keys. Wizard itself may use a remote managed model and trial credits: this is distinct from running the analytics agent locally. It requires verified free account access before use.

The alternative of starting with a local model would measure language quality and hardware behavior before proving the data boundary. Defer that expense until this spike passes. A plain hand-written fake planner alone would not prove Pydantic AI integration; exercise its real Agent/output validation path using a controlled test model.

## Repository context after refactoring

| Responsibility | Current source |
|---|---|
| Fact and enforced output contract | `transform/models/marts/fct_daily.sql` |
| Metric definitions | `transform/models/marts/semantic.yml` |
| Shared native unit fixtures | `transform/models/intermediate/unit_tests.yml` |
| Landing and ingestion fixtures | `transform/models/staging/cvm/` |
| Captured history | `transform/models/history/sat_daily_report.sql` |
| Safe snapshot patterns | `release/snapshots.py`, `release/uat.py` |
| Independent numeric oracles | `profiling/cvm/evidence/monthly-oracles.json`, `scripts/check_semantics.py` |
| Semantic mutation helper | `demo/mutations.py` (disposable tests only) |

Keep `.venv-dbt` and `.venv-mf` under `compatibility/dbt-v2-metricflow/` unchanged. Use a third isolated Python 3.12 environment for Pydantic AI and pytest. Pin actual resolved versions before acceptance; don't invent a lock from documentation. Dependency installation is separate from downloading model weights and remains a future spike step, not work performed by this review.

Model IDs are unchanged despite new FQNs/path components. Read serving metadata from the selected sealed bundle, not from today's source path or the mutable `data/demo/project`. Historical baseline bundles legitimately retain their old layout. Locate definitions by identity; do not rewrite the baseline to match new folders.

## Gate 0 — Wizard access (still pending)

The user last reported a domain but no dbt account. Account creation, eligibility, trial expiry and remaining credits have not been verified. The documented offer is a one-time 30-day / USD 100 trial, whichever ends first, with business-email eligibility and no required card. CLI login can start that trial. Do not assume a domain alone qualifies.

Complete signup personally, inspect the displayed trial state and ensure no paid billing is active. Only then install/verify the CLI and record `wizard doctor` plus version. Do not invoke `dbt wizard` as a read-only availability check: the installed CLI advertises that it installs Wizard if missing. Avoid starting the trial just to inspect a help screen. Stop if payment or paid-provider credentials are required. Never put tokens, email addresses or screenshots containing account data in the repository.

Source: [dbt trial policy](https://docs.getdbt.com/docs/dbt-ai/pricing-billing/trial-and-billing). The initial read-only Wizard planning request is allowed to consume verified trial credits; it is not an offline operation. Package setup may use the network separately. The deterministic test processes must run with outbound network denied.

## Gate 1 — bounded TDD task for Wizard

Use a dedicated branch when implementation is authorized. Proposed ownership: `compatibility/wizard-agent-spike/` containing README, dependency lock, `contract.py`, `gateway.py`, `planner.py` and `tests/`. Wizard may read existing specs/contracts but must not edit dbt models, existing locks, CI, production release pointers or agent goldens. Save evidence locally under `data/wizard-agent-spike/` and publish only sanitized summaries. This directory is not created by the present review.

Restrict the spike to PL and net flow, automatically paired with their coverage counts, for the frozen April–September cohort. Support total and month output, plus the known single-class/day missingness fixture. Other dimensions, user formulas, free-text filters, follow-up conversation, charts and general natural-language capability remain out of scope.

Validate strict typed output and business policy before process creation. Use a discriminated query/clarify/unsupported result, unknown fields forbidden. Scope values are enums or verified IDs; dates are bounded. Construct fixed executable/cwd/profile and argv arrays with `shell=False`; no model-chosen paths, environment, SQL, URI, release or executable. A string passed as one argv argument is not automatically safe SQL/Jinja.

Use Pydantic AI `FunctionModel` for exact valid/invalid scripted outputs; `TestModel` is suitable only where its generated output matches the test purpose. Set `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` before test-agent construction. It blocks accidental real model requests, not arbitrary HTTP or subprocess access; enforce network denial at the test-process boundary too. No provider API keys, hosted tracing or Logfire configuration. [Pydantic AI testing documentation](https://pydantic.dev/docs/ai/guides/testing/).

For fixture binding, use the existing durable baseline selected by `ci/baseline.lock.json`, verify its sealed bundle, and pin it once. This spike needs no production UAT pointer change. Record implementation commit and data release/bundle hash separately. The complete application still uses session-pinned UAT resolution as specified in AI-SPEC.

Follow `release.uat.collect()`'s temporary-project/read-only connection pattern; do not copy its broad inherited environment unchanged. Verify startup manifest/bundle hashes, then use the pinned MetricFlow executable. Parse CSV with Decimal and preserve nulls. Capture exact requested/actual grain, coverage, query hash and release provenance. Check explain/query compatibility on the installed CLI, not help text alone. If explain doesn't provide the required SQL binding, mark that gate failed instead of fabricating provenance.

## Acceptance cases (deterministic; all must pass)

| ID | Test | Expected evidence |
|---|---|---|
| W01 | Valid scripted Pydantic AI output | Real Agent/output-schema path produces canonical bounded intent |
| W02 | Unknown metric, extra SQL/path fields, malformed dates and injected filter | Rejected before any MetricFlow process starts |
| W03 | Clarify/unsupported scripted outputs | No data execution and no numeric answer |
| W04 | Two invalid outputs / repair budget | At most one repair; final typed error; no query |
| W05 | Real full-period query | PL `119385193058.06`, flow `4725910556.15`, counts `7554/7560` |
| W06 | Real monthly query | Six rows equal independent frozen monthly goldens; no sum of monthly PL |
| W07 | Known missing class/day and synthetic observed zero | Missing PL/flow remain null; observed zero remains zero |
| W08 | Read-only connection and bundle integrity | Trusted write-attempt fixture fails; bundle and DB hashes unchanged |
| W09 | Tampered bundle / mid-request pointer change | Fail startup on tamper; already-pinned request stays on original release |
| W10 | Deadline, process failure, oversized result | Typed error, no fabricated/truncated answer, descendants reaped |
| W11 | Explain and query | Same canonical arguments, snapshot and semantic hash; actual SQL artifact recorded |
| W12 | Network/provider boundary | Test process cannot call a model/provider or auto-download anything |

W01–W04 must use controlled Pydantic AI outputs, not an alternative planner implementation. W05–W06/W11 must use real MetricFlow; mocks cannot satisfy them. W07–W10 may use explicitly labeled synthetic failure fixtures where the real snapshot cannot safely express the case. Do not alter independent goldens. Demonstrate red then green for new validation boundaries; an unrelated import/connection failure does not count as a business rejection.

Finish with independent adversarial review of diff, subprocess arguments, permissions and negative evidence. Record Wizard version, trial verification time/usage, Python/framework versions, code revision, bundle and manifest hashes, test totals, query durations and limitations. Never call this a language-quality benchmark, a validated model choice or production readiness.

## Ready-to-use Wizard prompt

> Work only on the qualification spike specified in specs/wizard-agent-spike.md. First read specs/AI-SPEC.md, specs/metrics.md, specs/ai-agent-evals.md, CONTRIBUTING.md and the current sealed-snapshot interfaces. Summarize the contracts and propose file changes before editing. Once the spike is authorized, write failing boundary tests first, then implement the smallest Pydantic AI FunctionModel-to-MetricFlow integration that satisfies W01–W12. Preserve published PL/flow goldens, use a third isolated Python environment and a verified pinned snapshot, and prove real read-only execution. Do not install models, call a real analytics LLM, add payment details, configure paid keys, run Docker locally, modify dbt models or publication pointers, or claim mocked tests prove natural-language quality. Report failed gates honestly and preserve evidence for independent review.

Passing this spike qualifies the assistant/framework/data integration only. Next comes the full deterministic gateway; local-model download and benchmarking require a later explicit decision.
