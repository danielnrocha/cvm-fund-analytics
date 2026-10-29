# dbt repository development review

Reviewed **2026-10-28**, against main `e535e29` plus existing uncommitted agent specifications. Status: approved refactor implemented locally and validated; see [acceptance and review](../reviews/repository-refactor-review.md). The research baseline below is retained to explain the changes. Remote CI has not run for this local diff. No Docker, model downloads, billing changes or agent implementation.

## Recommendation

Organize the existing transformation project by responsibility, preserve model names and business behavior, and use native dbt v2 lint/format with a shared configuration. Keep `transform/` as the production project. Do not introduce another project, a full Data Vault framework, extra environments, or a second SQL formatter merely for convention.

Three options were considered:

| Option | Benefit | Cost | Decision |
|---|---|---|---|
| Style and documentation only | Small diff; low migration risk | Flat model directory remains harder to navigate | Useful first migration step |
| Layered model folders, shared style, focused documentation | Clear learning path and maintainability without changing the DAG | Must migrate scripts and demo references together | Recommended |
| Full repository/runtime relocation and modeling redesign | Cleaner long-term separation | Large unrelated diff, baseline/runtime risk and new concepts | Defer |

## Findings from the repository

| Priority | Finding | Action |
|---|---|---|
| High | 13 SQL models share one flat `transform/models/` directory | Group by responsibility; preserve filenames, `ref` names and schemas initially |
| High | No shared SQL style configuration; compressed SQL, implicit aliases and inconsistent indentation | Native lint/format with explicit DuckDB/dbt templater configuration; review fixes |
| High | Demo and semantic-mutation gates rely on paths and exact text | Update these consumers in the same change; assert each mutation actually occurs |
| Medium | `quality.yml` centralizes model docs; several source tables lack descriptions/column metadata | Colocate model properties and describe source grain, identifiers, dates and provenance |
| Medium | Production tooling lives under `compatibility/` | Document that these locks are active runtime dependencies; relocate only in a separate change |
| Medium | Root VS Code directory has tasks but no shared settings or extension recommendations | Provide one documented official-extension entry point, editor style and explicit dev target |
| Medium | All non-overridden models default to tables | Keep for this small frozen release; evaluate views separately with packaging/read-only tests |
| Medium | `current_daily` and satellite use wildcard projections | Prefer explicit output columns at stable boundaries; verify schema and decimal types |
| Low | Historical evidence is spread across several directories | Index evidence by purpose; do not rewrite old acceptance evidence as if regenerated |

Existing strengths: environment-based profiles, separate dev/UAT database paths, one writer per database, pinned runtimes, native unit tests, enforced fact contract, decimal arithmetic, missing-versus-zero semantics, immutable landing, quarantine, append-only history, semantic oracles, durable baseline and protected remote CI. These were inspected; the full acceptance suite was not rerun during this review.

Do not describe the current satellite/history implementation as a complete enterprise Data Vault. Its value is retained capture history and replay behavior. Adding hubs/links solely to satisfy a diagram would expand the demo without improving the agent's metric contract.

## Approved directory mapping

```text
transform/
  dbt_project.yml
  profiles.yml
  .sqlfluff
  .sqlfluffignore
  selectors.yml
  models/
    staging/cvm/       # landing sources, bronze_classified, stg_observations
    reference/         # entities, captures, report_calendar, time_spine
    intermediate/      # int_resolved, int_daily, current_daily
    history/           # sat_daily_report
    marts/             # fct_daily and its semantic properties/metrics
    audit/             # quarantine, audit_ingestion_files
  tests/               # existing singular invariant tests
```

Move the relevant YAML properties/unit tests with their models; retain each model definition exactly once. Keep shared multi-model unit fixtures together if splitting would duplicate them. The mapping describes responsibility, not a mandatory linear folder-to-folder DAG: `current_daily` consumes history, and `time_spine` serves metrics. No relation/schema renames in this migration.

Keep `ingestion/`, `release/`, `ci/`, `demo/`, `tests/`, and `specs/` at root. Distinguish Python tests under root from singular dbt SQL tests under `transform/`. Do not invent an empty agent package before implementation.

## Style contract

SQL: four spaces, lowercase keywords/functions/identifiers, trailing commas, explicit `as`, one selected expression per line and spaces around operators. Aim for 80 columns; use reviewed exceptions where splitting harms readability. Prefer descriptive aliases and explicit join conditions. Use named CTEs for logical transformations; do not add ceremonial CTEs to trivial pass-throughs. Preserve numeric scale, null handling, predicate placement and window ordering during formatting.

YAML: two spaces, indented sequences, multiline descriptions for long prose, stable ordering. Jinja: spaces inside delimiters, visually separated blocks, readable indentation. These follow the official [SQL](https://docs.getdbt.com/best-practices/how-we-style/2-how-we-style-our-sql), [YAML](https://docs.getdbt.com/best-practices/how-we-style/5-how-we-style-our-yaml) and [Jinja](https://docs.getdbt.com/best-practices/how-we-style/4-how-we-style-our-jinja) guides. Named grouping columns remain a deliberate local preference for teaching, even though the SQL guide prefers ordinal grouping.

Start with native `dbt lint` and `dbt format`, not a separate Python SQLFluff installation. Both are present in installed 2.0.9. Configure `.sqlfluff` with `dialect = duckdb` and `templater = dbt`; select a reviewed rule set, exclude generated artifacts, and keep format-on-save separate from lint auto-fixes. SQLFluff-compatible does not mean identical results. [Native lint reference](https://docs.getdbt.com/reference/commands/lint?version=2).

## Editor, configuration and CI acceptance

- Add root `.editorconfig`: SQL/Python four spaces, YAML/JSON two, LF and final newline; preserve Makefile tabs and Markdown hard breaks. Apply settings to the generated demo workspace too.
- Recommend `dbtLabsInc.dbt`; use only one active SQL formatter. Installed 0.122.0 exposes `dbt.formatOnSave`, `dbt.lintFixOnSave`, `dbt.dbtPath`, and `dbt.targetName`. Confirm engine support before enabling save actions; keep lint auto-fix off initially. No login needed to justify formatting setup.
- Make the active project, binary, profile and target explicit. A root multi-project repository and the disposable demo are different entry points. Never make a published snapshot the default write target. Disable unintended deferral in this self-contained demo.
- Introduce named selectors for the demonstrated vertical and audit scope only after validating their selected nodes. Keep full acceptance builds; do not replace semantic regression with `state:modified` checks prematurely.
- Keep dbt and MetricFlow environments separate. Do not install dbt-core plugins into the pinned v2 environment just to satisfy an older formatting recipe.
- Add fast lint/format checks before the expensive remote Docker build once the code passes. Keep the required `validate` check intact. Formatting success never substitutes for build, unit/data tests or semantic comparisons.
- Document commands and version provenance in CONTRIBUTING. Keep `.env`, DBs, raw bytes, credentials, generated targets and logs out of Git. The checked-in profiles contain local configuration, not credentials.
- Retain `--static-analysis strict --generate-info-schema` for lineage validation. Recheck model and column lineage after moves in the official extension.

## Tests, contracts and metadata

Model contracts enforce shape/types; unit tests check transformation cases; data tests check actual relations; semantic oracles check metric results. Keep all four. Add tests for meaningful gaps, not mechanically for every column. Document each stable model's grain and keys, each amount's currency/additivity, and reporting date versus captured time. The fact's existing descriptions are a useful pattern for the rest of the project.

Do not add a wall-clock freshness SLA to the frozen April–September dataset: it would become predictably stale. Document frozen provenance and existing manifest/calendar checks. A future live feed needs a separate ingestion freshness contract.

The official [staging](https://docs.getdbt.com/best-practices/how-we-structure/2-staging) and [intermediate](https://docs.getdbt.com/best-practices/how-we-structure/3-intermediate) guides support organization by source and business transformation. The [marts guide](https://docs.getdbt.com/best-practices/how-we-structure/4-marts) explicitly distinguishes Semantic Layer modeling from its general denormalization advice. Preserve the class/day grain and normalized semantic relationships; do not create extra joins or redundant aggregates for appearance.

References: [unit tests](https://docs.getdbt.com/docs/build/unit-tests), [data tests](https://docs.getdbt.com/docs/build/data-tests), [workflows](https://docs.getdbt.com/best-practices/best-practice-workflows), [official extension](https://docs.getdbt.com/docs/about-dbt-extension).

## Executed review checks

From `transform/`, with anonymous telemetry disabled and separate output paths:

```sh
../compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt lint \
  --profiles-dir . --no-version-check \
  --target-path ../data/repository-review/target \
  --log-path ../data/repository-review/logs

../compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt format --check \
  --profiles-dir . --no-version-check \
  --target-path ../data/repository-review/format-target \
  --log-path ../data/repository-review/format-logs
```

Results: lint processed 19 items and returned exit 1 with **38 errors / 30 warnings** under default rules. Format check returned exit 1 with **16 errors / 1 warning**. The templater warning is expected without `.sqlfluff`. These are a style baseline, not proof of incorrect business results. Source SQL was not rewritten. Local raw logs: `data/repository-review-lint.txt` and `data/repository-review-format.txt` (ignored).

## Migration sequence and proof

1. Agree this bounded structure/style design; freeze current model IDs, contracts and metric outputs as comparison inputs.
2. Configure native formatting/editor behavior, apply reviewed SQL/YAML formatting, and repair mutation scripts to fail if their intended edit did not happen.
3. Move model/YAML files without renaming nodes. Update demo paths, compiled-path instructions, `scripts/check_semantic_mutation.py`, `tests/ci/check_semantic_gate.py` and all source-path consumers. Preserve historical evidence.
4. Run fast Python tests, lint, format check, native unit tests and full dbt build in an isolated working database. Validate MetricFlow configs, exact totals, six monthly rows, missing/zero behavior, replay/corrections and both red/green exercises.
5. Inspect the regenerated DAG/column lineage; run remote Linux CI and semantic baseline comparison before merge. Do not rotate the baseline merely to accommodate formatting or path changes.

Post-refactor results are in the linked acceptance report. Native lint/format, folder layout, full build, metric equivalence, exercises and artifact lineage passed. Save integration and visual lineage were not newly inspected. The machine-scoped dbt.dbtPath setting must be configured at User scope; the generated workspace intentionally omits it.
