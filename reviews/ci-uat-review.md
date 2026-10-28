# Independent CI and UAT adversarial review

Review date: 2026-10-28. Scope: `release/uat.py`, `release/snapshots.py`, `scripts/snapshot.py`, `tests/release/test_uat.py`, and `ci/`. No Git metadata is available. Review is read-only except this report; real databases and published environment pointers were not modified.

## Final verdict

**PASS for the reviewed implementation and local Linux ARM64 container acceptance. No unresolved reproducible functional findings.** The P1 hidden-file transport issue was corrected and independently regression-tested. Earlier pending/failure entries below are retained as review history and are superseded by this final verdict.

Final evidence reviewed under `transform/evidence/ci/linux-acceptance/`:

- `result.json` records Linux/aarch64, non-bootstrap comparison `cvm-atomic-v2` → `cvm-linux-uat-v3`, four required lineage edges, PL `119385193058.06`, flow `4725910556.15`, and coverage counts 7554/7560.
- Independently recomputed all four CSV comparisons from `semantic-comparison.json` using the current comparator: no differences. Checked the exact baseline/candidate/expected tuple and query suite.
- Independently checked all 48 dbt resources in `run_results.json` have success/pass status. Read the Linux test logs and counted 13 business + 13 ingestion + 29 release + 15 CI = **70 passing Python tests**.
- Docs log records successful v2 generation, 13 documented models, the pinned driver digest, and the preserved manifest digest. Image metadata records Linux/arm64 and the global `ADBC_DRIVER_PATH` configuration.
- Negative semantic integration evidence records six monthly and one total difference, rejected promotion, and unchanged pointer. History, rejection, real-oracle, and semantic integration logs report PASS.
- Read-only checks of the actual local `dev` and `uat` pointer files confirm both still reference `cvm-atomic-v2`; the Linux acceptance candidate did not replace them.

The author executed the final acceptance command with Docker networking disabled and reported exit 0; this reviewer inspected its retained artifacts and independently recomputed the recorded semantic comparison, rather than rerunning the full container. The reviewed workflow and documented reproduction command enforce `--network none` after online bootstrap.

**Limits:** this accepts the local Linux ARM64 container path. No GitHub-hosted run or actual upload/download across GitHub runs has occurred; transport coverage is a local simulation against the configured hidden-file policy. No amd64 acceptance is claimed. Python dependency versions are pinned but distribution hashes are not. Filesystem ownership, validator code, and human baseline selection remain trusted, as declared. The repository has no Git/remote configuration, so remote governance and CI activation are outside the completed evidence.

## Historical interim result

No reproducible correctness finding in the implemented semantic gate under its explicitly declared trusted filesystem owner / trusted validator runtime model. Linux workflow and documentation validation review remain pending: `.github/workflows` was empty and `ci/docs.py` absent during the initial inspection. This is not evidence that Linux CI has passed.

## Evidence

- Ran `compatibility/dbt-v2-metricflow/.venv-mf/bin/python -m unittest discover -s tests/release -v`: 28 tests passed.
- Ran the four frozen-input downloader tests in `tests/ci`: all passed.
- Independently exercised `collect()` using a temporary bundle and a mock only at the MetricFlow subprocess boundary. All four subprocesses received the same exact resolved snapshot path and `config_options.access_mode=READ_ONLY`, with target `uat`, inside a disposable copied project. The original profile bytes were unchanged, and the temporary project was removed afterward.
- UAT promotion checks the previous pointer under the publication lock before validating the report. The gate is bound to baseline ID, candidate ID, expected pointer, both complete bundle-manifest hashes, input fingerprints, and the exact query suite. Stale pairs cannot be reused for another promotion.
- Result verification recomputes differences from recorded CSVs instead of trusting only the `passed` field. Required columns, every query, duplicate/empty groups, malformed values, nonfinite numbers, missing groups, null-versus-zero, and exact decimal differences fail closed. Row and column order and numeric formatting do not create spurious differences.
- Comparisons include total, month, day/entity, and coverage views. Opposite per-entity or per-period changes cannot disappear solely through aggregate cancellation.
- `build()` runs real-oracle and semantic checks before sealing; those checks retain literal PL `119385193058.06` and net flow `4725910556.15`. Build subprocesses remove `PYTHONOPTIMIZE`, and the CI entrypoint also rejects optimized execution.

## Boundaries and remaining verification

- The gate report is a local attestation, not a signed trust boundary. A malicious filesystem owner can rewrite both reports and bundle manifests; this is explicitly outside the current threat model, not a newly discovered bypass.
- Existing tests demonstrate the behaviors above, but source inspection and a green suite cannot establish historical red-before-green TDD sequencing without independent execution records.
- A real Linux network-disabled build, actual MetricFlow queries, docs generation, and final workflow artifact/baseline handling require separate execution evidence. None were substituted with the subprocess mock used for the narrow read-only profile check.

## Follow-up inspection: ARM64 runner and expanded checks

- Current workflow targets `ubuntu-24.04-arm`, builds and runs `linux/arm64`, and the entrypoint requires `Linux/aarch64`; these selections are consistent. Acceptance remains network-disabled with source bytes and the imported baseline mounted read-only. amd64 execution is explicitly not claimed in `specs/ci-uat.md`.
- Baseline download layout (`baseline/releases`) matches the uploaded `ci-output` tree. Normal PR/push execution requires an explicitly selected baseline; self-comparison is only available through the explicit manual bootstrap input.
- `ci/run.py` now calls the real semantic mutation script, history/rejection integration checks, and column-lineage acceptance. The mutation deliberately removes stock semiadditivity in a temporary candidate, reparses it, runs the live comparison, and asserts that a rejected promotion leaves the pointer bytes unchanged.
- Re-ran `tests/ci` after docs-integrity and lineage tests were added: 9 tests passed. Missing/corrupted documentation binaries and missing redemption lineage are rejected.
- `ci/docs.py` checks the pinned driver's size and SHA-256, requires the pinned dbt version, sets `ADBC_DRIVER_PATH`, and checks that docs generation preserves the build manifest. The online bootstrap removes the downloaded driver's cache directory after copying the verified binary.
- Final image bootstrap wiring, driver lock, and actual offline Linux result are still pending at this inspection. The review has not treated successful macOS tests as Linux proof.
- Minor documentation correction sent to the author: the general statement that logs/reports live outside bundles is too broad; sealed builds include their build/ingestion logs and validation report. The no-write claim correctly applies to gate collection against sealed bundles.

## Final implementation review (Linux acceptance remains blocked)

### P1 — Uploaded baselines lose hidden files and fail integrity checks

At this inspection `.github/workflows/linux-ci.yml` uploads `ci-output/` without `include-hidden-files: true`. The exact pinned upload action defaults this input to false: [pinned action definition](https://raw.githubusercontent.com/actions/upload-artifact/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml).

Sealing includes hidden files in `bundle.json`. Read-only inspection of the actual `cvm-atomic-v2` manifest found `project/.gitignore`, `project/.user.yml`, `project/target/private/index/.artifact_meta.json`, and `project/target/private/index/.fusion_state.json`. These are omitted from the default upload, so a downloaded baseline fails `_verify()` before comparison. This blocks the normal run after bootstrap even when the original build passed.

Reproduced safely by sealing a temporary fixture with `project/.gitignore`, removing only that temporary file to model the action's exclusion, and calling `_verify()`: `ValueError: Bundle checksum mismatch`. No real bundle or environment pointer was changed. Required fix: include hidden files in the scoped output artifact or package the complete release tree in an archive, and verify a roundtrip retains manifest content. Finding sent to the author immediately.

### Updated driver and test evidence

- Re-read the final compressed-driver bootstrap and lock. The bootstrap bounds compressed and unpacked sizes, checks the compressed digest before decompression, uses a bounded libzstd output buffer, checks exact output length and unpacked digest before writing, then publishes using an atomic replacement. The Dockerfile now calls the online bootstrap.
- The Linux ARM64 lock pins 86,705,784 unpacked bytes with SHA-256 `344d183eaaf97255b49a1a084497999a50989397444fe4aaf44bbbca19b66917`, plus compressed length/digest and official CDN URL. The earlier cache-based bootstrap description above is superseded by this implementation.
- Independently ran the final CI test suite: 12 tests passed, including successful decompression and rejection of both compressed and unpacked drift before driver persistence.
- Inspected `transform/evidence/ci/semantic-mutation.json`: records blocked promotion, unchanged pointer, six monthly differences, and one total difference. This is recorded integration evidence supplied by the implementation run, separate from the reviewer's narrow subprocess boundary check.
- Inspected `transform/evidence/ci/driver-download.json`: explicitly records `runtime_validated: false`. Download integrity is not runtime validation.
- Inspected the end of `13-linux-arm-image.log`: image extraction fails while writing `_duckdb.abi3.so` with `input/output error`. The author's reported host disk exhaustion is consistent with that failure, but the log alone does not prove the entire causal diagnosis.

### Acceptance decision

The semantic gate has no unresolved finding under its declared trust model. The workflow has the P1 artifact-content finding above until corrected. Full Linux ARM64 acceptance and Linux documentation execution remain unproven and blocked by the failed image extraction; no green Linux result exists. No approval of offline Linux CI is implied by passing macOS tests or driver download integrity. The specification explicitly records that runtime limitation; its remaining phrase describing ARM64 as already "homologado" should be replaced with intended/target platform wording.

## P1 remediation verified

The hidden-file transport finding is **resolved** in the current implementation. The upload step now explicitly sets `include-hidden-files: true` for the scoped `ci-output/` artifact. The new `tests/ci/test_transport.py` reads that actual workflow setting, models its file selection, ZIP-roundtrips a sealed fixture containing hidden project and dbt files, and verifies the restored bundle with `_verify()`.

I independently ran that test: 1 passed. I also inspected the retained red log (`23-transport-red.log`), which fails with the predicted `Bundle checksum mismatch` before the option was enabled, and `24-ci-green.log`, which reports all 13 CI tests passing afterward. This establishes regression coverage for the concrete content-loss defect; the test explicitly does not claim to execute GitHub Actions. The specification's premature ARM64 homologation wording was corrected to intended platform wording.

**Current code-review verdict:** no unresolved reproducible functional findings in the reviewed gate/CI implementation under its declared trust model. **Separate runtime verdict:** offline Linux ARM64 acceptance and Linux docs execution remain pending until a successful end-to-end run is produced. The author reports disk space was recovered and a new Linux attempt is planned; that environmental change is not itself acceptance evidence.

## Linux-driven implementation corrections reviewed

The subsequent Linux run exposed two concrete runtime issues; the author corrected both and requested focused re-review. `ci/Dockerfile` now exports `ADBC_DRIVER_PATH=/workspace/ci/drivers` for the entire offline runtime, so native dbt build and all inherited subprocesses can use the prepared driver, not only the docs subprocess. `ci/docs.py` now validates the dbt v2 documentation outputs (`index.html` and a nonempty `info_schema/v1/dbt.models.parquet`) instead of requiring the legacy `catalog.json`. The manifest-before/after integrity check remains in place.

I inspected both changes and independently ran the expanded CI tests: **15 passed**. The documentation tests cover acceptance of the v2 artifacts without a legacy catalog and rejection of missing HTML. The project's build workspace is freshly created with `target` excluded from the source copy, so this validation does not inherit stale HTML from a previous build workspace. Logs `26-linux-offline.log` and `29-linux-offline.log` record the earlier build and docs failures, respectively.

No additional functional finding from this focused review. Prior image-extraction/disk blockage is superseded by actual Linux execution; however, the final complete offline run is still pending at this checkpoint. Partial native build, oracle, or semantic success is not recorded here as full Linux acceptance.
