# Portfolio preparation independent review

Date: 2026-10-28. Scope: current uncommitted repository preparation, durable baseline transport, GitHub Actions wiring, Docker-free development commands, attribution and portfolio claims. No commit SHA exists yet. This review does not certify a published repository or remote CI execution.

## Assessment

No blocking correctness or security findings identified in the reviewed increment. The implementation separates durable Release assets from expiring Actions artifacts, verifies both archive and inner bundle integrity, and fails closed when the required baseline is unavailable. Read-only workflow permissions and disabled checkout credential persistence fit the public-portfolio use case. Manual bootstrap is explicitly differentiated from normal baseline comparison and cannot publish a replacement baseline.

README and publication specification distinguish implemented capabilities, historical Linux acceptance, and pending remote execution. Private-release authentication, dependency distribution hashes, upstream source availability, repository protection and release immutability are documented limits or pending operator work rather than claimed completed controls.

## Findings

### P3 — VS Code build tasks do not share the Makefile entrypoints — resolved

Location: `.vscode/tasks.json`, tasks `CVM: build and test` and `CVM: semantic oracles`.

The new `make build` fetches and verifies inputs, ingests them, runs strict dbt with information-schema generation, and checks SQL oracles. The existing VS Code build task invokes dbt directly and omits these steps. Consequently, choosing that task on a fresh checkout after setup does not reproduce the README's build sequence; semantic tasks also bypass `make metrics` configuration validation. The delivery plan explicitly requests a single command source for Make and VS Code.

Resolution independently verified: both tasks now invoke `make build` / `make metrics` from `${workspaceFolder}`, retaining the semantic task dependency on the build task. No findings remain open.

## Evidence independently checked

- `make test`: **77 tests passed** natively (13 business, 13 ingestion, 29 release, 22 CI).
- Seven baseline tests cover hidden-file roundtrip, archive byte drift, deterministic packing, path traversal, wrong release identity, existing destination preservation and corrupted inner bundle.
- Actual `dist/cvm-baseline-v1.zip`: **3,251,493 bytes**, SHA-256 **5904eb6deac37cd2158ecb8c8500b9dae68b04ed461a00ee2dcf363fb78bc59c**, matching the committed-intent lock; 295 archive members.
- `_verify('baseline/releases', 'cvm-linux-uat-v3')` succeeded against the restored real baseline.
- A narrow text scan of common textual archive members found no `/Users/` or `/home/` paths. This is not a comprehensive secret scan.
- Inspected baseline pack/restore/fetch, tests, workflow, Dockerfile and ignore rules, Makefile, README, data attribution, release notes, portfolio specification, relevant delivery-plan sections and runtime entrypoints.

## Targeted follow-up verification

The deterministic archive test now actually changes a source file timestamp with `os.utime` between pack operations. All seven baseline tests passed again after this change. VS Code task changes were inspected directly; no full build or remote execution was implied by that check.

## Limits

No Docker invocation, new Linux acceptance, live Release download, GitHub repository mutation or remote workflow run was performed. The previous 70-test Linux run remains historical evidence; the 77-test result here is native Python validation of the current increment. Clean-machine dependency installation and complete local build/docs were not rerun by this reviewer. The first real published Release download and normal GitHub Actions run remain required operational acceptance.
