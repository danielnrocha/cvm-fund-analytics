# Contributing

Use `make setup`, then `make test`. For model or metric changes run `make build` and `make metrics`. No local Docker is required. The complete Linux acceptance runs in GitHub Actions.

Describe the business behavior, input grain and metric impact in the PR. Add a failing fixture before changing logic, then run the relevant checks. Keep frozen oracles unchanged unless the source or business contract change has been explicitly reviewed.

Do not update the baseline hash to make a failing PR green. A baseline change requires a separately reviewed release, new tag/asset and a lock update. Release assets, raw archives, virtual environments, generated databases and credentials do not belong in Git.

Protected `main` requires a PR, an up-to-date `validate` check from GitHub Actions, resolved review conversations and linear history, including administrator changes. Use squash merge after the current revision passes. Force-pushes and deletion are disabled. Second-person approval is optional for this sole-maintainer portfolio; see [policy and acceptance evidence](specs/main-protection.md).

## dbt development conventions

`transform/` is the active dbt project. `compatibility/dbt-v2-metricflow/` currently owns the pinned dbt and MetricFlow runtime locks; it is not safe to delete it as an obsolete experiment. Keep these environments separate. Run from the repository root:

```sh
make lint format-check test
make format                 # explicit layout changes; review the diff
make build metrics          # isolated release acceptance is stronger than a dev build
```

SQL uses four spaces, lowercase keywords, trailing commas, explicit aliases and an 80-column target. `.sqlfluff` is consumed by native dbt v2; no separate SQLFluff installation is needed. Layout formatting and lint fixes are different operations. Never blindly apply lint fixes: DuckDB tuple DISTINCT is intentionally exempt from ST08, and projections/casts retain documented local conventions. YAML uses two spaces and indented lists. Preserve decimal scale, null/zero behavior and incremental replay semantics.

Models are organized by responsibility: `staging/cvm`, `reference`, `intermediate`, `history`, `marts`, and `audit`. Folders do not rename database schemas. Keep node names stable during structural changes and colocate YAML properties. Native fixtures that span several layers remain together under `intermediate/unit_tests.yml`; ingestion fixtures live beside staging. Singular dbt SQL tests live in `transform/tests`; Python lifecycle and business tests live in root `tests`.

For the official VS Code extension, open `data/demo/official-dbt.code-workspace` after `make demo-prepare` (or an intentional reset). Preparation pins the terminal binary through env.sh, selects the editor dev target, disables deferral, and recreates the workspace file. The extension setting `dbt.dbtPath` is machine-scoped: set it in VS Code User settings to the absolute path printed by `realpath compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt`, not in workspace settings. Verify dbt 2.0.9 in the extension status/output before presenting. This user setting affects other workspaces; restore your previous value when switching projects. Reset discards disposable edits. The repository-level settings supply shared editor defaults; the generated workspace is the isolated teaching entry point. `dbt: Format File` is the explicit fallback if engine format-on-save is unavailable. Keep lint auto-fix on save disabled. No Wizard login is required for these checks.

For every structural refactor, validate the full build, MetricFlow totals/monthly/gap queries, native red/green exercise, semantic red/green exercise and column lineage. Preserve historical evidence and immutable baseline assets. Regenerate candidate evidence; do not edit old evidence to make it describe new source files.
