# Independent live-demo review

Reviewed 2026-10-28 against base `b0ea64e`, while the parent task was still preparing final rehearsal evidence and reconciling the delivery plan. Scope: disposable lifecycle, rehearsal assertions, presenter instructions, YAML descriptions, docs project selection, and test integration. No Docker, original database mutation, live demo workspace mutation, publication, or commit was performed.

## Findings — both resolved on re-review

1. **P2 — Validate all reset prerequisites before deleting the existing workspace.** `demo/workspace.py:54–60` checks only database existence/WAL before removing the owned workspace; `prepare()` subsequently rejects source-project symlinks and may fail on a missing source project. A reproducible case is preparing a workspace, adding a symlink under `transform/models`, then calling reset: it raises `ValueError: Source project must not contain symlinks` after the old workspace has already disappeared. This defeats reset as a dependable recovery path and destroys the previous usable rehearsal even when invalid prerequisites were detectable beforehand. Share preparation validation with reset before removal; preferably stage the replacement before replacing the owned directory. Add a regression that preserves the old workspace on invalid source inputs.

2. **P2 — Identify the actual frozen-oracle mismatch in the semantic red step.** `demo/rehearse.sh:48` accepts any `AssertionError`. `scripts/check_semantics.py` also raises `AssertionError` when its MetricFlow subprocess fails, or when row counts/coverage differ. The separate broken-total checks prove that the edited stock metric is wrong and flow remains correct, but a transient monthly query failure can still be credited as the independent frozen oracle rejecting that stock. Require evidence that the monthly query succeeded and the assertion names `reported_net_assets_eop` with the actual mismatching row, or expose a structured mismatch result. Reject unrelated connection/query failures.

Resolution verified on 2026-10-28: shared `validate_sources()` now runs before reset removes the workspace and rejects missing/linked projects, missing project configuration, linked databases and WAL. The added failed-reset regression preserves existing rehearsal notes. The semantic red verifier now requires the exact `reported_net_assets_eop` assertion signature, six monthly rows, and an independently wrong September stock in addition to wrong total/correct flow. These changes close both reported findings. No remaining actionable findings were identified in the re-reviewed scope.

## Verified strengths and checks

- Deferred code-review-graph discovery and `get_minimal_context_tool` succeeded (3,122 nodes, 14,822 edges); source inspection provided the detailed review.
- `python3 -m unittest discover -s tests/demo -v`: seven tests passed on re-review, including preservation after invalid source input.
- The reset failure above was reproduced only in a temporary directory.
- Ownership marker, bounded `data/demo` destination, parent/workspace/descendant symlink rejection, copied database, fixed disposable profile and absent UAT output provide meaningful isolation for the documented single-presenter workflow.
- The SQL red check verifies both the named native fixture and null-to-zero output, avoiding the common “any nonzero is success” problem.
- The semantic exercise preserves the closing-count rules, independently checks the wrong stock and unchanged flow, and restores/reruns the full existing real-data checks.
- The runbook distinguishes existing tests from new TDD work, model versus column lineage, synthetic fixtures versus real observations, prior PR evidence versus a new live gate, and automated duration versus spoken presentation duration.
- The docs project override retains the existing checksum verification and network-blocked driver execution.

## Evidence limits

The current runbook, spec and delivery-plan reconciliation were re-read and agree on the practical prepared-project scope and the separate spoken rehearsal requirement. The parent reports integrated-browser column-lineage verification and has saved a screenshot; this reviewer did not independently interact with that browser. Three final complete rehearsals after fixes, source/database/pointer hashes, and the final acceptance record are owned by the parent task and were pending during re-review. This report does not certify those unfinished acceptance items. Historical PR claims were not independently revalidated against GitHub in this review.

## Final offline orchestration re-review

Inspected the final `demo/rehearse.sh` wrapper without executing or touching the demo workspace. The documented no-argument entrypoint runs build, queries, both mutation cycles and lineage in a network-denied subprocess, then invokes pinned docs separately; the latter retains its own network/global-cache-denied sandbox. This avoids the parent-reported nested macOS sandbox failure without removing either execution boundary. `set -euo pipefail` propagates subprocess and docs failures, and the final success line is reached only after both return successfully. Repository-root discovery also makes the internal re-entry independent of the sourced environment's working-directory change. No blocker identified. `--offline-steps` is an internal entrypoint; offline acceptance should continue to use the documented no-argument command.

The parent reported one successful final run (23.78 seconds; maximum RSS 403,505,152 bytes) and 84 passing full-suite tests. These measurements were reported by the parent, not independently rerun by this reviewer; remaining repetitions and consolidated acceptance remain parent-owned.
