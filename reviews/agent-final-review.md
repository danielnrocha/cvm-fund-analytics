# Independent final branch review

Reviewed on 2026-11-04: `c884ebcf4d16095aa5c48776b20a6f196ae2b7d0..a2ae910b8513ade2344b6bc6fe04172ce3c45b91`.

**Code verdict: approved for the implemented deterministic gateway and experimental single-turn planner, with two minor corrections below. No Critical or Important code defect was established. Production natural-language readiness: not accepted.** Missing acceptance evidence is a separate release blocker, not a claim that the reviewed safety boundary is broken.

## Scope and evidence

Static review covered the branch's runtime modules, contracts, catalog, OAuth source and transport construction, worker boundary, Decimal result validation, renderer, evaluation runner and independent oracle derivation, test coverage, CI/Make/VS Code integration, demo instructions, implementation plan, AI-SPEC and evaluation contract. The earlier Task 1, Task 3 and Task 4 scoped reviews and corrections were also inspected. One concrete adversarial path was traced through the actual-adapter regression: it opens a disposable snapshot with the production profile, attempts a database write and local/remote file reads, and verifies denial and unchanged bytes. The separate wrapper regression exercises socket denial; timeout tests exercise descendant cleanup.

The reported 80-test required agent suite, 88 existing tests, lint/format checks and 18-family/84-row deterministic oracle replay were not rerun. No credential file, OAuth session or external inference was accessed, and no Docker was used. Holdout question wording was not inspected. Live quality figures below are operator-reported evidence, not trials performed by this reviewer. In-progress edits to planner settings and acceptance evidence after the reviewed commit are outside this verdict.

## Findings

### Critical

None found.

### Important

None found in the reviewed implementation.

### Minor

1. **Qualify the public hard-deadline claim.** `specs/AI-SPEC.md:140` promises a 60-second end-to-end hard deadline. The CLI starts its clock before gateway construction (`agent/cli.py:90,100`), but startup bundle verification and the initial database hash have no deadline parameter (`agent/gateway.py:44,62`). Synchronous filesystem calls can also delay a timeout response after startup. Thus a slow local verification can run past 60 seconds before returning a typed timeout. The existing late-result checks correctly prevent accepting a late numeric answer, and the configured snapshot is trusted/operator-selected; this is not a model-controlled bypass. Carry the already acknowledged limitation from the Task 1 re-review into the public contract: distinguish worker termination budgets and late-result rejection from an OS-enforced total wall-clock limit. If a literal hard bound remains required, put the invocation behind a supervising process that can terminate it. Include cold startup in operational qualification; do not claim a hard wall-clock guarantee from the existing deadline tests.

2. **Include the trusted available range in out-of-snapshot refusals.** `agent/cli.py:48-50` renders only `Unsupported: outside_snapshot.` when alternatives are empty. Alternatives can contain metric IDs only, so they cannot supply the April–September 2026 range required by AI-SPEC business policy 7. A user asking for last month gets no actionable indication of the dates they can query. Render a fixed outside-snapshot template using the already verified catalog's start/end dates, and add a focused CLI rendering check. Keep the dates application-owned rather than adding free-form model output. This fails safely today and does not produce incorrect financial values.

## Architecture and regression assessment

- The model emits a strict discriminated intent and has no registered tools. Unknown fields, metrics, dimensions, unsafe filter values, unsupported presentations and excessive estimated cardinality are rejected before a MetricFlow worker starts. Execution revalidates a detached intent, including nested mutable fields.
- Snapshot identity, source fingerprints, semantic definitions and runtime versions are bound before execution. The session stages its pinned wrapper and manifest bytes. Explain and execution use the same validated arguments, and actual executed SQL must match explain output before a result is accepted.
- The worker uses argument arrays, an isolated profile/environment and process group, read-only DuckDB, external-access/extension restrictions, bounded files and per-invocation waits. Its trust model is accurately limited to a trusted single OS user and approved runtime, rather than a hostile-code sandbox.
- Application-owned OAuth avoids the shared CLI credential loader. Private atomic storage, session locking, endpoint checks, proxy/redirect restrictions, disabled retries and explicit request/output limits are present. Public reports correctly distinguish client acceptance limits from a server-side spending cap.
- Monetary results remain Decimal; the gateway injects supporting counts and checks population/calendar denominators, effective cuts, null versus zero, partial coverage and row completeness. The global PL, net flow and count invariants are covered by real gateway checks. Independent sidecar derivation does not invoke the implementation under test.
- CI runs the third isolated environment without inference, against the sealed candidate, and fails required-mode omissions. The deterministic demo explicitly labels its mode. The renderer and provider-error paths avoid raw untrusted text, credentials and provider bodies.

## Incomplete acceptance, separate from code findings

At review time the operator reported development iteration 2 at **69/72 exact decisions, 30/33 supported queries and numeric trials, and 55/57 critical cases**. These results do not meet the critical-case gate. A subsequent reasoning-profile experiment is in progress and is not covered by this review. The first development run and these follow-up results are development evidence, not untouched holdout acceptance.

Before a natural-language production or go-live claim, the owner still needs:

- A fixed candidate/configuration and the prescribed repetitions with all critical cases passing; untouched held-out intent, supported-query and numeric gates, with complete denominators and sanitized provenance.
- The specified hidden-value end-to-end fixture qualification, distinct from the existing synthetic parser/result-boundary test. Multi-turn A19/A20 remain explicitly unsupported and must not be claimed as implemented single-turn behavior.
- Operational evidence including cold startup, warm latency, resource behavior and recovery. Passing warm development latency alone does not establish those gates.
- A successful run of the updated remote Linux CI, and review of any subsequent runtime/configuration corrections. Production activation, exact post-merge revision validation, local demo acceptance and safe retirement of the owned worktree remain the release owner's closeout responsibilities.

The runner's numeric source guard currently binds original input-source fingerprints, while the oracle evidence also records the exact snapshot digest. The reviewed sealed baseline is the qualified oracle source. Before extending live acceptance to other releases, bind the numeric run to that verified snapshot digest or independently derive and freeze new oracle evidence; a matching input-source fingerprint alone does not prove identical derived facts.

A scoped re-review should inspect the two minor corrections and any final runtime/configuration diff. This review does not authorize promotion based solely on deterministic tests or on an average development score.

## Scoped re-review — fixes through `1662135`

Reviewed `a2ae910..de7e283` and the instruction-only `de7e283..1662135` diff on 2026-11-04. This is a static re-review of the changes and their focused regression, without repeated tests, inference, credential access or holdout wording access.

- **Minor 1 resolved.** AI-SPEC now describes the shared monotonic deadline, bounded worker waits and rejection of late numeric results, explicitly distinguishes these from an OS-enforced wall-clock limit, and includes startup verification in cold latency qualification. The public planner report states the same filesystem limitation. No runtime deadline enforcement was weakened.
- **Minor 2 resolved for the natural-language CLI.** `_print_result` appends the available dates for `outside_snapshot` using `gateway.get_catalog()` (`agent/cli.py:40-42`). The dates come from the verified application catalog rather than model output. The focused regression exercises the normal `ask` path with a controlled refusal and a real configured gateway, checking both the refusal and exact available range. Plan-only remains structured output; a standalone non-query plan file can still run without a gateway or OAuth.
- **Instruction revision approved as a development change.** The additional instructions distinguish captured-classification filters from reporting-class grouping and explicitly identify period versus closing coverage. They agree with the existing capability catalog and business semantics. The diff changes no schema, expected answer, oracle, worker, credential path, provider, request budget or gateway policy. Candidate and reasoning profile remain `gpt-6-luna` / `low`. The prompt change invalidates prior model-quality acceptance for the changed instructions, so the focused development result is supporting evidence only.

The owner reports five CLI and three deadline regressions passing, and nine focused development prompts passing after the instruction revision. This reviewer did not rerun those checks. The owner also reports the full development run is underway; no result from that run or from holdout is assumed here.

**Updated code verdict: approved for the reviewed deterministic gateway and experimental single-turn planner; both minor findings are closed. No new Critical, Important or Minor finding was identified in the scoped diff.** Production approval remains conditional on the separate model, numeric, hidden-value, operational, remote-CI and exact-revision/closeout gates above. This appendix closes the implementation review findings; it does not promote the natural-language capability or replace those acceptance gates.
