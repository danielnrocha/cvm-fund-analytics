# Repository refactor — adversarial review and acceptance

Date: 2026-10-28. Base: `e535e29`. Changes are local and uncommitted; no remote run or merge is claimed.

## Independent review

A separate read-only reviewer inspected SQL semantics, YAML equivalence, incremental behavior, mutation helpers, CI packaging and extension setting scopes. Initial YAML equivalence passed for 13 models, 12 unit tests, two top-level metrics and one source. Subsequent source metadata additions document existing columns without changing transformations.

- Tuple DISTINCT must retain parentheses. Native lint auto-fix incorrectly removed them during development; restored before acceptance, with a documented local ST08 exception. Existing duplicate-conflict unit tests passed.
- P2: `dbt.dbtPath` is machine-scoped in extension 0.122.0. Removed it from generated workspace settings after a failing regression test. User-level configuration and runtime version verification are now explicit in the runbook. No global preference was changed. Existing extension output and LSP logs report 2.0.9; this is not proof of a workspace-scoped binary override.
- Minor: style checks initially ran only after Docker construction. Added an earlier GitHub Actions step using the pinned dbt requirements; retained checks in the offline runner.

## Executed acceptance

- `make lint format-check test`: native lint and format pass; 88 Python tests pass (13 business, 13 ingestion, 29 release, 22 CI, 11 demo).
- Native isolated CVM build: 48 successes (13 models, 23 data tests, 12 unit tests).
- MetricFlow validate-configs and real queries: six monthly oracles, totals, filtered missing report, and coverage pass. PL = 119385193058.06; net flow = 4725910556.15.
- Offline rehearsal: both red/green exercises fail for the intended business reason, then pass. Original SQL and semantic YAML restored byte for byte. Used a separate scratch workspace, preserving the user's existing demo directory.
- History: delta A/B/A, idempotent replay and full rebuild pass. Rejection gates for required fields, capture FK and immutable replay pass.
- Final candidate `refactor-v2` versus sealed `cvm-linux-uat-v3`: zero semantic differences across total, monthly, daily/entity and coverage probes.
- Old sealed-baseline mutation: regression blocked; UAT pointer unchanged; six monthly and one total differences detected.
- Final model manifest: all 13 unique IDs and dependency sets equal the baseline. Four required column-lineage edges pass, including JSON payload to PL and both cashflow components to net_flow.
- Selectors: daily_vertical selects 12 model ancestors including the fact; ingestion_audit selects exactly the two audit models. Time spine remains available to full builds.

The expected dbt1005 cloud-manifest warning remains; local MetricFlow validation runs independently. Historical UI screenshots were not regenerated or presented as new visual evidence. Post-refactor lineage was checked through generated artifacts, not a new manual UI inspection.

## Evidence locations

Ignored local logs: `data/refactor-final-checks.txt`, `data/refactor-rehearsal.log`, `data/refactor-history.txt`, `data/refactor-rejections.txt`. Candidate build and semantic logs: `data/refactor-acceptance/work/dev/refactor-v2/`. Sealed candidate and gate report: `data/refactor-acceptance/`. Compact negative proof: `data/refactor-old-baseline-negative.json`.

No Docker ran locally, no baseline asset was replaced, no environment was promoted in the user's release root, and no AI agent or local model was installed. GitHub Actions workflow was updated but not triggered in this task; Linux acceptance remains to be run on publication.
