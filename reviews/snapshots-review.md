# Snapshot publication adversarial review

## Revalidation verdict — 2026-10-28

**PASS for the five reported findings within the local same-host, trusted-owner scope.** All five baseline findings below are resolved by the reviewed revision. No outstanding blocker was reproduced in this revalidation. This verdict does not claim administrator-proof immutability or empirical power-loss recovery.

Independent checks used only temporary directories and executed the current implementation through the MetricFlow Python environment:

| Baseline finding | Independent revalidation evidence | Result |
| --- | --- | --- |
| Source-copy provenance race | Editing the source immediately after copy now raises `Source changed during copy` before any validator runs. Changing only the copied model while keeping the source unchanged raises `Copied project differs from source fingerprint`. Editing source during mocked validation raises `Source changed during validation`. None publishes a bundle. | Resolved |
| Incomplete source inventory | Temporary nested model and macro files both appear in `source_hashes()`. Code now recursively inventories supported executable/configuration file extensions across source trees. | Resolved for current project inputs |
| Nested bundle.json bypass | A sealed temporary `project/bundle.json` was changed; resolving the published release rejects the checksum mismatch. Only the root manifest is excluded. | Resolved |
| Directory durability gaps | Instrumented `_sync` while still executing actual fsync calls. Confirmed project/models/nested → project/models → project → staging synchronization before rename; confirmed synchronization of every newly created root ancestor, snapshots parent, environments parent, and final environment directory. | Resolved ordering gaps; no power-failure simulation |
| PYTHONOPTIMIZE disables gates | Set parent environment `PYTHONOPTIMIZE=1`; intercepted all five subprocess calls during a successful temporary mocked build. Every child environment omitted the variable. | Resolved |

The repository suite independently passed **13 tests**, with the previous inherited duplicate tests removed. The temporary successful builder test used mocked ingestion/dbt/semantic subprocess results and a real temporary DuckDB checkpoint/seal; it proves orchestration and environment handling, not business correctness. The parent agent reports a successful real `cvm-atomic-v2` UAT build with optimized parent environment; that real build is separate evidence and was not rerun or modified by this reviewer.

Source inventory intentionally excludes generated directories and seeds, matching the current no-seed builder. Adding new executable file types or restoring seeds requires extending both capture and provenance coverage. The trusted-builder and release-ID CAS boundaries documented below remain applicable.

Reviewed file SHA-256 values:

- `release/snapshots.py`: `752b0ea72dd0a9b501b191193cc98abeaf6bada1807cc9d76ca9d4d9136f8e3a`
- `scripts/snapshot.py`: `73a4bf90b5cba7d06b8e07be5bb7b789b629ba48369081857e446c79c92ec570`
- `tests/release/test_snapshots.py`: `266c6d47fbcd350cc623e978d91a3f0fc535f24e1c79e33a19f65569bdb977f2`

Only this review document was modified. No scripts, models, real bundles, landing objects, or main database were changed by the reviewer.

## Baseline review (historical; findings resolved above)

Reviewed 2026-10-28. Scope: local same-host filesystem, trusted owner; no claim of administrator-proof immutability. Review baseline: initial implementation of `release/snapshots.py`, `scripts/snapshot.py`, `transform/profiles.yml`, and `tests/release/test_snapshots.py`. Findings below describe that baseline; subsequent fixes require revalidation.

## Findings

1. **P2 — Source identity can differ from the copied and validated project.** `scripts/snapshot.py:17-20` copies the project before taking the first source digest. An ordinary concurrent editor can change a model in that interval, leaving the copied model at revision A and both digest samples at revision B. The build accepts this and its validation provenance incorrectly identifies B. Temporary-directory reproduction, with subprocess validation mocked: copy `select 1 as old`, mutate source to `select 2 as new` immediately after copy, call `build`; resulting sealed project contains old SQL while source hashes identify new SQL. Take the baseline before copying and verify both the copied project and live source against it; ideally execute all validator code from the captured source set.

2. **P2 — Source inventory omits nested models/tests and other executable dbt inputs.** `scripts/snapshot.py:11` uses one-level globs. A temporary nested `transform/models/nested/ignored.sql` was absent from `source_hashes()`. Macros and other project inputs also have no coverage. Recursive inventory of the actual captured project, excluding only generated artifacts, avoids provenance gaps.

3. **P2 — Nested files named bundle.json bypass integrity checks.** `release/snapshots.py:28` excludes that basename at every depth, although only the root manifest should be excluded. Temporary reproduction: seal a candidate containing `project/bundle.json`, change its contents, promote, resolve; both operations accept the alteration. Exclude only the root-relative `bundle.json`.

4. **P2 — Crash durability is incomplete for nested and newly created directories.** `release/snapshots.py:53-55` fsyncs files and the staging root but not project/models, project/target, or other nested directories. `_write` creates environments and its environment directory but only syncs the final environment directory; snapshots/root creation likewise does not persist all new parent entries. Atomic rename protects concurrent visibility, but does not alone guarantee the complete namespace survives a host crash. Sync nested directories bottom-up and persist new ancestor directory entries before acknowledging publication. This is a filesystem ordering review, not a power-failure reproduction.

5. **P2 — Optimized Python can silently disable validation comparisons.** `scripts/snapshot.py:19` inherits `PYTHONOPTIMIZE`; both real-oracle and semantic checker scripts use `assert` for the comparisons establishing correctness. With optimization enabled these gates are removed even though subprocess completion is recorded as validation success. Remove the environment option for validator children or use explicit exceptions for release gates.

## Positive evidence and boundaries

- Existing unit discovery passed all 18 executions; inheritance repeats eight cases, leaving ten unique scenarios.
- A separate temporary-directory multiprocess test launched two publishers with expected release `a`; exactly one publication succeeded and the other rejected its stale expectation. The filesystem lock protects the read/compare/write sequence.
- Separate dev/UAT pointer paths, no in-place overwrite of existing releases, a single reader pointer lookup, and read-only DuckDB consumer connections implement the intended pinning/isolation design under the trusted-owner assumption.
- Existing fault injection covers replace failure before the pointer change and retaining a previously resolved path. It does not simulate power failure, actual DuckDB readers across publication, source-capture races, or optimized validators.
- `seal` treats `validation.json` as a trusted builder assertion. Tests intentionally seal arbitrary database bytes with only `{passed:true}`. It is not an independent verification of database correctness; document this trust boundary and do not expose it as a verifier of arbitrary caller-supplied candidates.
- A release-ID CAS allows ABA (a → b → a). This is consistent with comparing the current immutable release identity. If the desired contract is rejecting any intervening publication, add a monotonically increasing generation token.
- All reviewer execution used temporary directories and test fixtures. No real release, landing objects, or main database was changed.

## Verification commands

`compatibility/dbt-v2-metricflow/.venv-mf/bin/python -m unittest discover -s tests/release -v`

Additional inline Python checks used TemporaryDirectory, mocked subprocess validation for the source-copy race, and forked publisher processes for concurrent CAS.
