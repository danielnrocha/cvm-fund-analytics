# Independent business fixture review

Reviewed 2026-10-28 against `specs/data-contracts.md` and `specs/metrics.md`. Scope is the reduced synthetic executable specification, not CVM ingestion, dbt or MetricFlow delivery.

## Findings

### P2 — Derived net flow has insufficient precision

`tests/business/probe.py`, `summarize`: the temporary table declares `flow DECIMAL(17,2)`. The data contract gives that precision to each source amount, CAPTC_DIA and RESG_DIA, without a nonnegative constraint. Their difference may require DECIMAL(18,2).

Reproduced with one typed fact: entity A, date 2026-04-01, PL `Decimal('1.00')`, flow `Decimal('999999999999999.99') - Decimal('-999999999999999.99')`. Both source amounts fit the contract. Actual: DuckDB `ConversionException`, value `1999999999999999.98` out of range. Expected: exact reported flow `1999999999999999.98`, one present/expected observation, complete coverage. Widen the derived flow column and add this boundary oracle. This is an aggregation defect within the reduced probe, not a request for a parser.

### P3 — Contract implementation status needs a scope update

The final sentence of `specs/data-contracts.md` says domain contract tests and integration fixtures will still be implemented. The new suite now executes synthetic business-contract examples. Distinguish these implemented examples from pending production/domain integration tests so the document neither hides the suite nor implies it validates the full pipeline.

## Evidence

- Fresh execution: `compatibility/dbt-v2-metricflow/.venv-mf/bin/python -m unittest discover -s tests/business -v` — 12 tests pass.
- Reviewed red evidence: 12 tests, 14 failed assertions including subtests; green evidence: 12 pass. These logs demonstrate the stated before/after outcomes, but are not independently replayable proof of the historical implementation state.
- Literal oracles cover duplicate preservation, conflicting payload rejection, A/B/A capture separation, namespace/subclass distinction, identity ambiguity, join fanout/missing matches, cutoff gaps and empty population.
- The overflow reproduction above fails outside the current test matrix.

## Limitations and verdict

The probe deliberately uses a reduced PL/flow payload and synthetic identity mappings. It does not establish full-payload CVM deduplication, lexical ingestion validation, historical identity continuity, real-source reconciliation, incremental equivalence, or MetricFlow correctness. Those are not required to approve this bounded fixture scope. The A/B/A test establishes capture separation, not an incremental engine.

**Verdict: request the small precision correction before closing this suite; otherwise the reviewed duplicate, gap, identity and fanout examples behave as asserted.**

## Re-review after correction — 2026-10-28

Both findings are resolved. Inspected the temporary table's new `flow DECIMAL(38,2)` and the added literal boundary oracle for `1999999999999999.98`. A fresh independent run of the documented unittest command passes all **13 tests**, including that reproduction. The new red log records the expected assertion failure caused by the original conversion overflow; the final green log agrees with the fresh run.

The data contract now explicitly separates implemented synthetic contract tests from pending parsing, dbt models and pipeline integration. Its precision explanation matches the correction. The fixture scope document and README retain the necessary limitations.

Inspected the mutation runner, six mutation results and their assertion failures. Each mutation changes a meaningful behavior in a disposable copy; the recorded failures exercise duplicate inflation, capture separation, subclass distinction, arbitrary dimension selection, cutoff retreat and null-to-zero substitution. These mutation results were inspected, not rerun during this re-review (the runner writes evidence files outside reviewer ownership).

**Final verdict: approve the bounded synthetic business-fixture suite. No unresolved findings from this review.** This approval does not certify production ingestion, dbt, MetricFlow or the full pipeline; the limitations above remain applicable.
