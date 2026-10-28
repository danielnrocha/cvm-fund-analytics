# Protected main and semantic PR acceptance

Repository: [danielnrocha/cvm-fund-analytics](https://github.com/danielnrocha/cvm-fund-analytics). Policy configured on 2026-10-28; the declarative request is versioned in [main-protection.json](../.github/main-protection.json). This file records configuration; GitHub does not apply later file edits automatically.

## Merge policy

- Changes to `main` require a pull request, including changes by administrators.
- The GitHub Actions application (ID `15368`) must report the exact check `validate` as successful, with the PR branch up to date with `main`.
- Linear history is required; use squash merge. Force-push and deletion of `main` are disabled.
- Review conversations must be resolved.
- Required approving-review count is **zero** for a sole-maintainer portfolio. PR visibility, CI and review-thread resolution are enforced, but this is not a mandatory second-person approval policy. Increase the count once a second maintainer is available.
- Manual `bootstrap=true` uses the check name `bootstrap-certification`, which cannot satisfy the required `validate` check. Normal PRs, pushes and non-bootstrap dispatches use `validate` and compare against the pinned Release baseline.

A green native dbt build alone is insufficient: `validate` also runs real MetricFlow baseline/candidate comparison and fails before promotion on semantic differences. The workflow's only upload step may run after failure to preserve diagnostics; that does not convert a failed job into a passing check. The release baseline and its hash are not refreshed by a PR.

## Trust boundary

The check is bound to GitHub Actions and its name, not to an immutable workflow implementation. Repository administrators can change protection; trusted workflow editors can change what a check executes. This protects normal development against regressions, not against a malicious repository owner or deliberately weakened validator. A second independent reviewer / separate protected governance boundary would be needed for that stronger threat model. No bypass of the configured policy is used in this validation.

## Controlled PR exercise

[PR #1](https://github.com/danielnrocha/cvm-fund-analytics/pull/1) contains a deliberately failing intermediate revision and a corrected final revision. The temporary mutation changes only the semantic definition of `net_flow`, adding BRL 0.01 on April 1 and subtracting BRL 0.01 on April 2 for `CVM:CLASS:621`.

The two underlying observations both have net flow zero. The mutation preserves monthly/total oracles while introducing two class/day differences. It is intended to exercise the independent semantic comparison, rather than merely failing a SQL unit test. It must never be merged into `main`.

After inspecting the failed check and merge-block state, restore the original metric definition, retain only policy/workflow documentation changes, rerun remote CI, and squash merge only after GitHub reports the PR ready. Record actual run results below. No local Docker is used.

## Normal contributor workflow

1. Branch from current `main`; use native `make test`, `make build` and `make metrics` as appropriate.
2. Push the branch and open a PR. The required Linux check runs on the GitHub-hosted ARM64 runner, inside Docker with the acceptance network disabled.
3. Inspect failures and fix the candidate. Do not change the baseline to make an unexplained regression pass.
4. Update the branch if `main` advances, resolve conversations, and wait for `validate` on the current revision.
5. Squash merge through GitHub, then verify the post-merge run on `main`.

## Recorded acceptance

On 2026-10-28, [negative run 40770238983](https://github.com/danielnrocha/cvm-fund-analytics/actions/runs/40770238983) failed the required `validate` check at head `4e82cdcb4dff403386db69c8c6d28589f29b908f`. GitHub reported `mergeStateStatus: BLOCKED`. The semantic report contained exactly two `daily_entity.net_flow` differences (+0.01 and -0.01); total, monthly and coverage comparisons were unchanged. UAT remained on `cvm-linux-uat-v3`. [Compact evidence](../transform/evidence/pr-validation/negative.json) preserves the report identifiers and differences without duplicating the full query results.

The final PR diff restores the original metric expression. Final-head and post-merge checks are available in [PR #1 checks](https://github.com/danielnrocha/cvm-fund-analytics/pull/1/checks) and [main run history](https://github.com/danielnrocha/cvm-fund-analytics/actions/workflows/linux-ci.yml?query=branch%3Amain). A passing earlier revision does not authorize merging a newer revision.
