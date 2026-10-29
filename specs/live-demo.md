# Live demo acceptance — 20–25 minutes

Scope: package the implemented CVM vertical as a repeatable teaching session. No new data source, Vault framework, hosted semantic service, AI agent, local Docker, or deployment is required. This is presentation readiness, not completion of the full architecture roadmap.

## Teaching contract

Audience: practitioners who know dbt fundamentals. The central question is: **can an apparently valid query still publish a wrong business result?** Show a native unit test catching missing-to-zero conversion, then a semantic oracle catching time aggregation of a stock. Real data: 60 reporting classes, April–September 2026. Currency: nominal BRL. This cohort is not a market census.

The facts use a dense class/day grain. `reported_net_assets_eop` is a closing stock at a common date; `net_flow` is additive over time. Coverage accompanies interpretation. CVM source ZIP/CSV bytes are preserved; JSON envelopes are derived transport, not a claim of native JSON disclosures. The history model is a minimal capture satellite, not a complete Data Vault.

## Isolation and reset

`make demo-prepare` verifies the locally restored pinned baseline bundle, copies its closed database, and copies the current `transform` source into `data/demo/project`. It creates a dedicated profile pointing only to `data/demo/demo.duckdb`. The workspace has no UAT target. It never downloads, ingests new sources, promotes a snapshot or writes the original database. Current code is validated against frozen baseline inputs by the subsequent native build and oracle checks.

Use a dedicated terminal and source `data/demo/env.sh`; commands expose the real dbt and MetricFlow binaries. Preparation refuses an existing directory. `make demo-reset` discards only the marked workspace and re-creates it from the verified baseline/current source. Reset refuses missing ownership or symlinks. It removes exercise artifacts and edits; copy desired rehearsal output elsewhere first. Stop docs servers and dbt/MetricFlow before reset. This is a single-presenter workspace, not a concurrent workspace manager.

Dependencies, baseline download and docs-driver preparation happen explicitly before the session. Cached input availability is distinct from offline execution. `make build` remains the development ingest/build entrypoint; the stage script does not call it.

## Exercises and acceptance

1. Start from green: native build (48 resources), semantic validation and frozen real-data oracles.
2. SQL red: replace `d.pl` with `coalesce(d.pl, 0)` in the disposable `fct_daily.sql`. The existing native unit test must identify missing PL becoming zero, not merely return a nonzero process code.
3. SQL green: restore the expression and rerun that same test.
4. Semantic red: remove only the `non_additive_dimension` rule for `reported_net_assets_eop`. Parsing and the MetricFlow query must succeed; PL must differ from `119385193058.06`, while flow stays `4725910556.15`. The independent frozen oracle must reject the result.
5. Semantic green: restore the rule, parse and rerun all real MetricFlow oracles (six months, total, a filtered gap and coverage).
6. Compile strictly; require the four real column-lineage edges already checked by CI. Generate docs with the checksum-verified Darwin driver. Inspect the browser experience independently from the artifact check.
7. Reset and rerun in three automated rehearsals, recording time and memory. A 20–25-minute spoken session still requires the presenter's own rehearsal; automated command timings do not prove speaking time.
8. Preserve hashes of source models, original database and dev/UAT pointers across exercises. Mark all fallback evidence as previously executed, with revision/time.

## Deliverables

- [Presenter runbook](../demo/RUNBOOK.md): exact commands, edits, expected outcomes, timing and fallback.
- `demo/workspace.py`: bounded preparation/reset; `tests/demo`: lifecycle regression tests.
- `demo/rehearse.sh`: executable check of the complete red/green sequence, using real tools.
- Descriptions in the dbt YAML for visible grain, units, absence, capture time and aggregation policy.
- [Acceptance record](../demo/evidence/acceptance.json), raw logs kept locally, and independent adversarial review.

## Deferred

Full hubs/links and dimensional history, CDA/holdings, returns, AI BI tools/evals, Slim CI, microbatch and additional infrastructure remain outside this session. No advanced VS Code lineage panel is promised without direct validation. GitHub PR regression evidence is prepared beforehand; do not wait for a full remote run on stage.

## Acceptance result

Three final technical rehearsals passed on macOS ARM64: 23.78, 21.81 and 22.15 seconds. Maximum RSS reported by `time -l` was 403,505,152 / 444,383,232 / 472,940,544 bytes; this is not total system memory consumption. All 84 Python tests passed, the native build passed 48 resources, both intentional regressions were observed and restored, four column edges passed, and docs model/column graphs were visually verified in the integrated browser. Source project files, the original development database, baseline database and dev/UAT pointers retained their hashes. No local Docker was executed.

[Independent review](../reviews/live-demo-review.md) identified two issues, both corrected and rechecked: reset now validates source inputs before deletion, and semantic red requires the named PL mismatch rather than a generic assertion. The offline harness uses separate network-denied processes for exercises and docs because macOS rejects nested sandbox-exec. Earlier failed harness attempts are not counted among the three accepted runs.

Raw logs are kept locally in `data/demo-rehearsals/`; compact evidence and the lineage screenshot are versioned. The remaining presentation-specific action is the presenter's spoken rehearsal.

## Repository refactor acceptance (2026-10-28)

The runbook now uses layered model paths and official-extension entry points. Preparation/reset recreates `official-dbt.code-workspace`; the binary override is a User setting, not a workspace setting. Fail-closed mutation helpers support both old sealed baseline YAML and the new layout. Both offline red/green exercises passed and restored exact original bytes in a separate scratch workspace. [Full results](../reviews/repository-refactor-review.md). Existing screenshots remain historical evidence; fresh column lineage was checked in generated artifacts.
