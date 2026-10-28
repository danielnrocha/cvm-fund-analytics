# First vertical independent review

Reviewed and revalidated 2026-10-28. **Final verdict: PASS for the bounded frozen-snapshot vertical. All three initial findings are resolved for ordinary incremental `dbt build`.**

Scope: frozen 60-class CVM snapshot, native dbt v2 tests, DuckDB models, append-only capture satellite, dense daily mart and local PL/flow/coverage MetricFlow queries. No production parser, general Vault framework or AI capability review.

## Independent execution evidence

All executions used temporary project copies excluding shared databases, targets and logs. The shared database was never opened or modified. Binaries were the project's `.venv-dbt/bin/dbt` and `.venv-mf/bin/{python,mf}`.

- Complete real-data `dbt build` passed, including native unit and data tests. Independent SQL assertions reproduced all six monthly PL/flow oracles exactly as Python Decimal, monthly closing counts of 60, and 7,560 dense pairs with 7,554 reported observations.
- The latest `scripts/check_semantics.py` passed against a separately built temporary real database: six monthly exact money/count oracles, whole-period stock versus flow, a filtered missing entity/date without backfill, and coverage queries.
- The latest `scripts/check_history.py` passed in its isolated database: delta captures A/B/A, old-date correction, idempotent replay and rebuild from retained historical input.
- Independently reapplied all four negative cases to the full 7,554-row seed: null kind, null PL, orphan capture and changed existing capture payload. Each complete build failed. `target/run_results.json` explicitly marked both `current_daily` and `fct_daily` as skipped. Full contents of satellite, current and fact tables equaled their pre-failure contents after every rejection.

Re-review harness: `/tmp/cvm_rereview.py`. Initial diagnostic harnesses: `/tmp/cvm_adversarial_review.py` and `/tmp/cvm_review_real.py`. These are local review evidence; permanent integration runners are the scripts above and `scripts/check_rejections.py`.

## Initial findings and resolution

### 1. Changed existing capture payload silently ignored — resolved for incremental builds

Initially, PL 100 changed to 105 under the same capture/source/entity/date returned 100 incrementally, then 105 after full refresh; both builds passed. The added `snapshot_immutable.sql` test compares incoming and persisted business payload, source set and capture time. A changed replay now fails before downstream current/fact publication. The rejected test case preserves existing satellite/current/fact contents.

### 2. Missing mandatory business fields certified by coverage — resolved

Initially, null kind and null PL passed and yielded `(pl=NULL, reported=1, expected=1)`. Level validation now handles null kind explicitly. `required_observation_fields.sql` blocks null required identity, provenance, date and numeric values, and negative investor counts. Both independently tested missing-kind and missing-PL cases now fail with downstream publication skipped.

### 3. Orphan capture relationship silently erased observations — resolved

Initially, the satellite's inner join silently discarded an observation with an unknown capture, while a full build passed. `observation_capture_exists.sql` now rejects the relationship failure upstream. The independent orphan test fails and preserves the published snapshot.

## Positive design checks

The dense calendar preserves missing versus zero. Registry aggregation prevents ambiguous identities from multiplying observations. Conflict detection includes all six business values, including equal PL with differing flow. Derived flow uses DECIMAL(38,2). Separate capture IDs preserve A/B/A rather than deduplicating on payload alone. These are appropriate boundaries for this first vertical.

## Explicit limitations

- Full refresh deliberately reconstructs authoritative retained input; it is not an immutable replay audit against a prior database. Rebuild equivalence was demonstrated using unchanged retained captures, not by accepting arbitrary mutation of the authoritative input.
- The immutability test runs after the satellite model. It protects downstream publication, but does not make the complete build transactional. A mixed batch containing new versions and an invalid replay could append new satellite versions before the replay test fails. The independently tested pure rejection cases did not modify the satellite. Atomic ingestion of an entire mixed batch is not established here.
- Rejected builds can replace staging/intermediate tables and seeds. Preservation verified here concerns the published current/fact tables, and the satellite in the tested cases. Consumers must use the published models and the governed `dbt build` path; `dbt run` alone does not execute these gates.
- This is a pinned-source importer, not a general precision/schema quarantine parser. Verified source hashes constrain the accepted snapshot; lexical validation and capture acquisition behavior for arbitrary future sources remain outside scope.
- The semantic runner checks monthly EOP coverage for all six months and explicitly checks April's period ratio; exact observation numerators/denominators are checked for every month. It does not exhaust every possible category filter or empty interval.
- Latest-available PL, investor-account metrics, API metadata/status formatting and AI evals are not delivered by this narrow PL/flow/coverage vertical. No general production-readiness claim follows from this verdict.
