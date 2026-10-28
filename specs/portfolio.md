# Portfolio publication and durable baseline

Decision, 2026-10-28: GitHub Actions is the canonical CI executor. Docker runs on the GitHub-hosted Linux ARM64 runner; local development uses Python virtual environments, `make` and VS Code, without Docker. Local Linux containers remain an exceptional diagnostic option, not a prerequisite or background service.

## Repository identity

Approved name: **`cvm-fund-analytics`**. The English description and topics are maintained in [`.github/repository.json`](../.github/repository.json). The README leads with the semantic regression gate and separates implemented capabilities, remote activation and the roadmap. This metadata file is a publication input, not an automatically applied GitHub configuration.

## Repository state

The repository is initialized locally on `main`. There is no remote, public repository, initial commit or remotely executed workflow yet. Preparation does not imply publication. The root README presents implemented behavior separately from the full Data Vault and AI BI roadmap; data attribution is in `DATA_SOURCES.md`. No code license has been selected; no permissive license is implied by the portfolio.

Source control excludes raw archives, databases, drivers, virtual environments, local tooling indexes, user state, generated targets, release ZIPs and raw logs. Historical evidence is scoped and is not a badge claiming remote CI passed. A scan of publishable source filenames/content found no home-directory paths or common GitHub/private-key credential patterns; this is a narrow check, not a general secret-scan certification.

## Durable baseline contract

The committed `ci/baseline.lock.json` selects:

- Release tag: `baseline-v1`.
- Asset: `cvm-baseline-v1.zip`.
- Snapshot: `cvm-linux-uat-v3`, approved in the prior Linux ARM64 offline run.
- Size: 3,251,493 bytes.
- SHA-256: `5904eb6deac37cd2158ecb8c8500b9dae68b04ed461a00ee2dcf363fb78bc59c`.

The prepared asset is `dist/cvm-baseline-v1.zip` (ignored by Git). `ci/baseline.py` packs only the selected verified bundle, preserving all manifest members including hidden files. Its restore checks outer size/hash, archive bounds and paths, duplicate entries, regular files only, exact release identity and the complete inner bundle checksums. Invalid input never publishes a partially restored destination; existing destinations are not overwritten.

Normal PR/push CI downloads the public asset from the current repository's Release URL without credentials, restores it to `baseline/releases`, and compares the candidate against the locked ID. This is intended for a public portfolio; private-release authentication is not implemented. Missing/deleted assets, changed bytes and changed frozen input contracts fail closed. No automatic self-baseline fallback exists. `bootstrap=true` remains an explicitly labeled manual diagnostic/certification run; it does not update the baseline lock or upload a Release.

Actions artifacts keep a 14-day retention for diagnostics. They are **not the source of the approved baseline**. A Release asset is outside the Actions artifact-expiry policy, but administrators can still delete a release/repository; keep the prepared offline copy. Enable GitHub release immutability before publishing, upload all assets to a draft, then publish. Hash pinning catches replacement regardless of that setting. [GitHub artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts) · [Release immutability](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes).

A maintainer who can modify workflow, lock and validator remains trusted. Require review/branch protection on `main`; the hash is neither a signature nor an authorization policy. Normal CI has read-only repository permissions and cannot publish/overwrite the baseline. A new baseline requires a new release tag, archive, explicit review and lock update. Do not use `--clobber` or change hashes to hide a regression.

## First publication runbook

The repository name is selected: `cvm-fund-analytics`. Choose the personal account and a code license before public release. The following are operator steps, not actions already executed. Review `git status --short` and the publication set before the first commit.

```sh
# From the project root; replace OWNER/cvm-fund-analytics with the chosen public repo.
git add .
git diff --cached --stat
git commit -m "Add CVM analytics portfolio and semantic UAT gates"
gh repo create OWNER/cvm-fund-analytics --public --source . --remote origin
```

Apply the prepared description and topics after repository creation (replace `OWNER`):

```sh
gh repo edit OWNER/cvm-fund-analytics \
  --description "$(python3 -c 'import json; print(json.load(open(".github/repository.json"))["description"])')" \
  --add-topic "$(python3 -c 'import json; print(",".join(json.load(open(".github/repository.json"))["topics"]))')"
```

In repository settings, enable release immutability and temporarily disable Actions for the first push, avoiding a normal run before the required asset exists. Then:

```sh
git push -u origin main
git tag baseline-v1
git push origin baseline-v1
gh release create baseline-v1 dist/cvm-baseline-v1.zip \
  --repo OWNER/cvm-fund-analytics --verify-tag --draft \
  --title "Approved CVM semantic baseline v1" \
  --notes-file specs/baseline-release-notes.md
# Check the uploaded draft asset and hash, then publish:
gh release edit baseline-v1 --repo OWNER/cvm-fund-analytics --draft=false
```

Re-enable Actions, then dispatch **without bootstrap**:

```sh
gh workflow run linux-ci.yml --repo OWNER/cvm-fund-analytics --ref main -f bootstrap=false
```

Inspect the first remote result before adding a passing badge. Configure the `validate` job as a required check on `main`, subject to the account's available controls. Forks can use the same pinned asset by copying it to the same tag in their own public repo; no owner identifier is hardcoded.

## Local development

Use `make setup`, `make test`, `make build`, `make metrics` and `make docs`. These do not launch Docker. The two virtual environments keep the dbt v2 CLI separate from MetricFlow's Python dependency stack. Current local acceptance is macOS ARM64; Windows is not claimed. Setup and the first driver/source acquisition use internet. Publishing the development database remains a separate explicit snapshot command.

The immutable baseline does not preserve the mutable upstream raw CVM archives. Existing source hashes are enforced and caches are rechecked. Upstream drift may require restoring the retained raw archives or a reviewed capture refresh; the pipeline will not silently substitute data. This is a remaining long-term source-availability constraint, distinct from baseline retention.

## Validation of this increment

Seven baseline tests were run red before implementation, then green: hidden-file roundtrip, byte drift, deterministic packing, traversal, wrong release, preservation of existing destination and inner checksum corruption. The real approved Linux bundle was packed and restored locally with full manifest verification. The full native Python suite passed 77 tests; Docker was not started for this preparation. The restored real database preserved PL `119385193058.06`, net flow `4725910556.15` and coverage `7554/7560`. Workflow YAML and embedded shell syntax were checked. [Preparation evidence](../transform/evidence/portfolio/preparation.json).

The preceding Linux acceptance (70 Python tests, 48 dbt resources) remains historical evidence. New workflow Release download, first remote execution, immutability settings and repository protection must be verified after publication; they are not claimed as completed here.
