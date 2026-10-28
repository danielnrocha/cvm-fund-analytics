# Independent main protection review

Reviewed 2026-10-28 against PR #1 head `4e82cdcb4dff403386db69c8c6d28589f29b908f`, the working-tree workflow change, saved policy, and live read-only GitHub API responses. No Docker execution or remote mutation was performed by this reviewer.

## Verdict

No actionable implementation findings in the reviewed protection policy, bootstrap check-name separation, restored semantic model, and final documentation/evidence changes. Negative remote acceptance is independently verified below. Final positive acceptance remains pending; the current working tree is suitable to submit for that check.

## Verified configuration

- Live `main` protection matches `.github/main-protection.json`: strict `validate` check bound to GitHub Actions application ID 15368; protection enforced for administrators; PR required with zero approvals for the sole-maintainer workflow; linear history and conversation resolution required; force pushes and branch deletion disabled.
- At review time PR #1 was `BLOCKED`, with the `validate` check in progress in run `40770238983`.
- The proposed job display name evaluates to `bootstrap-certification` only for explicit manual bootstrap execution, and `validate` for ordinary PR/push/manual comparison runs. Its condition matches the existing `BOOTSTRAP` condition. A successful bootstrap run therefore cannot satisfy the ordinary required check after this change is applied.
- The temporary semantic mutation affects only class 621 on April 1 and April 2 by opposite one-cent amounts. It is appropriate for distinguishing daily/entity comparison from total/monthly comparison; actual changed rows and the rejection cause must still be established from the run evidence.
- The CI entrypoint propagates subprocess failure, requires explicit baseline selection for ordinary runs, and invokes comparison/promotion before writing a successful result.

## Acceptance requirements for the planned flow

Retain the negative run's exact commit and conclusion, and inspect its artifacts/logs to establish that daily/entity drift caused rejection while total/monthly comparisons remained unchanged. An unrelated build/download failure does not prove the intended gate. Restore the semantic model before final validation, ensure the restoration is visible in the final PR diff, and obtain a successful required `validate` check for the final PR head after all workflow/documentation changes. Recheck protection and mergeability immediately before squash merging. Record the resulting main revision and any required post-merge run separately.

## Trust boundary

The required check is bound to a GitHub application and check name, not an immutable workflow implementation. Repository owners and trusted workflow editors remain capable of changing validation logic or creating another Actions check with the same name. Owners can also edit branch protection itself. This policy is an ordinary enforced review/CI path for a trusted sole maintainer, not resistance to a malicious repository owner. The zero-approval setting intentionally does not provide independent human approval. The saved JSON records intended configuration; it does not automatically reconcile future remote drift.

The code-review graph entry point succeeded and reported low structural risk for these configuration changes. That result was used as an index, not as proof of GitHub enforcement.

## Negative acceptance and restored candidate verified

After run `40770238983` completed, a fresh read-only GitHub response showed `validate: FAILURE` and `mergeStateStatus: BLOCKED` on head `4e82cdcb4dff403386db69c8c6d28589f29b908f`. Independently recomputed differences from all four recorded CSV result pairs in the downloaded gate report using the repository comparator: exactly two `daily_entity.net_flow` differences for class 621, April 1 (+0.01) and April 2 (-0.01), and no total/monthly/coverage differences. The downloaded UAT pointer still references `cvm-linux-uat-v3`. The compact committed evidence matches the full report's identifiers, bundle hashes, differences and rejection result.

The working-tree `transform/models/semantic.yml` has no diff against `origin/main`: the deliberate mutation is restored. Inspected the updated README, contributor instructions, policy specification, CI/portfolio/delivery specifications and compact negative evidence. No merge blocker identified. Final-head successful `validate`, squash merge, and post-merge acceptance remain separate required evidence; this review does not claim those future steps passed.
