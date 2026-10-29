# CVM Fund Analytics — presenter runbook

Target duration: **20–25 minutes**, with a prepared project. This is not a from-empty-folder workshop. Commands below are run in a dedicated terminal. The exercise edits occur only under `data/demo/project`. Keep the source repository open alongside that folder in VS Code so the audience can distinguish the disposable project.

## Before the audience arrives

From the repository root, with network available if setup is needed:

```sh
make setup  # first installation only; skip when environments are already prepared
compatibility/dbt-v2-metricflow/.venv-mf/bin/python ci/baseline.py fetch --repository danielnrocha/cvm-fund-analytics
compatibility/dbt-v2-metricflow/.venv-mf/bin/python compatibility/dbt-v2-metricflow/pinned_docs.py --prepare --verify-only
make demo-prepare  # use make demo-reset if this owned workspace already exists
bash demo/rehearse.sh
```

The baseline fetch verifies the pinned Release archive and bundle. The docs command copies/verifies an already bootstrapped Darwin ARM64 driver from the local cache; if it is missing, bootstrap explicitly before the session using `pinned_docs.py --bootstrap`, then verify again. It must not silently download during the presentation. Local setup is validated on macOS ARM64; Linux CI has its separate pinned driver.

After rehearsing, leave the restored green workspace and generated docs ready. Do not reset just before presenting unless you also rerun the preparation build below. Open `data/demo/official-dbt.code-workspace` in VS Code. Preparation recreates this workspace with the dev target, formatting defaults and deferral disabled. In VS Code **User** settings, set `dbt.dbtPath` to the absolute path of `compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt` and confirm version 2.0.9 in the extension status/output. This setting is machine-scoped and cannot be pinned in the workspace JSON; restore a previous setting when using other projects. Use the official dbt extension; no login is required for the demonstrated development features.

The local dbt CLI may emit `dbt1005` because no `dbt_cloud.yml` is configured. The separate local `mf validate-configs` and metric queries are the semantic validation used here; no cloud login is required.

In the dedicated presentation terminal:

```sh
source data/demo/env.sh
# The shell is now in data/demo/project.
"$DBT" --version
"$DBT" build --profiles-dir . --static-analysis strict --generate-info-schema
"$MF" validate-configs
"$PY" "$DEMO_ROOT/scripts/check_semantics.py"
"$PY" "$DEMO_ROOT/compatibility/dbt-v2-metricflow/pinned_docs.py" --project .
```

Start the docs server in a **second** terminal, from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory data/demo/project/target
```

Open `http://127.0.0.1:8765` in the integrated browser. This serves generated compiled artifacts only on loopback. Stop it with Ctrl-C after the session and before reset.

## 0–3 minutes — the business trap

Say: “We have 60 reporting classes, not every Brazilian fund. What was their reported closing net asset value, and what cash flowed during the interval?”

```sh
"$MF" query --metrics reported_net_assets_eop,net_flow
"$MF" query --metrics reported_net_assets_eop,net_flow,reporting_coverage_period --group-by metric_time__month --order metric_time__month
```

The terminal may render large values in scientific notation; the CSV outputs and independent oracles retain the exact amounts.

Expected full-period PL: **119,385,193,058.06 BRL**. Net flow: **4,725,910,556.15 BRL**. Explain that the first number is a stock at the common closing date, while the second is a sum over the interval. A missing report is not zero and the cohort is not a market estimate.

## 3–6 minutes — trace the number

In the official extension, open `models/marts/fct_daily.sql`. Use its model actions to run the model, compile/view compiled SQL, and open lineage. For predictable command visibility, use the VS Code integrated terminal with the equivalent commands below. Use the extension's test/build actions where offered; terminal execution remains the fallback and is required for local MetricFlow. The right-hand Copilot chat is not dbt Wizard.

```sh
"$DBT" run --profiles-dir . --select fct_daily
```

Explain that `run` materializes a model but does not establish test acceptance. The preparation `build` ran models and tests together; the next exercise uses `test` explicitly.

```sh
"$DBT" ls --profiles-dir . --select +fct_daily --resource-type model
"$DBT" compile --profiles-dir . --select fct_daily --static-analysis strict --generate-info-schema
```

Open `models/marts/fct_daily.sql`, `models/marts/semantic.yml`, and the compiled `target/compiled/cvm_demo/models/marts/fct_daily.sql`. Show `ref()`, the class/day calendar, the left join preserving missing reports, explicit decimal types and the enforced output contract. Explain `run` builds models, `test` checks them, and `build` orders models and tests together, including native unit tests.

In the official extension, open the column lineage action for `net_flow` and trace both inputs. As a fallback in generated docs, choose **Models → fct_daily → General** to see model lineage. Choose **Columns → net_flow**, expand its chevron and scroll to see `subscriptions` and `redemptions` flowing into the metric input. This column view was visually verified in the integrated browser; [recorded screenshot](evidence/column-lineage.png). Trace upstream models as time allows. Distinguish model lineage from column lineage. The four required column edges are verified from the generated Parquet; do not claim automatic JSONPath-level lineage. Use the lineage fallback described below if the docs UI cannot expose the desired column view quickly.

## 6–11 minutes — native unit test, red then green

Open `models/intermediate/unit_tests.yml`, test `dense_calendar_keeps_missing_distinct_from_zero`. Explain the tiny A/B fixture: one observed zero is valid; absent class/day values must remain null. The test already captures the business requirement, before the deliberate code change.

In **the disposable** `models/marts/fct_daily.sql`, change only:

```sql
-- Correct:
    d.pl::decimal(17, 2) as pl,
-- Deliberately wrong:
    coalesce(d.pl, 0)::decimal(17, 2) as pl,
```

Run:

```sh
"$DBT" test --profiles-dir . --select dense_calendar_keeps_missing_distinct_from_zero
```

Expected: nonzero exit, the named test fails, and the diff shows `NULL -> 0.0`. dbt v2 records this mismatch as `error` in `run_results.json`; that label does not mean the expected business failure was absent. An unrelated compilation/connection failure is not a successful demonstration.

Restore `d.pl::decimal(17, 2) as pl,` and rerun the **same command**. Expected: one successful native unit test. The test fixture is synthetic; do not present its A/B rows as actual CVM observations.

## 11–18 minutes — valid SQL, wrong business metric

Open `models/marts/semantic.yml`. Under **only** `reported_net_assets_eop`, remove this block (leave the closing entity-count rules intact):

```yaml
        non_additive_dimension:
          name: report_date
          window_agg: max
          group_by: []
```

```sh
"$DBT" parse --profiles-dir .
"$MF" query --metrics reported_net_assets_eop,net_flow
"$PY" "$DEMO_ROOT/scripts/check_semantics.py"
```

Expected: parse and query succeed; PL is now a sum of daily stocks and wrong, while flow remains correct. The frozen monthly oracle rejects it. This proves a syntactically valid metric can still violate business semantics. Do not update the oracle to make the demonstration pass.

Restore the removed block under `reported_net_assets_eop`:

```sh
"$DBT" parse --profiles-dir .
"$MF" query --metrics reported_net_assets_eop,net_flow
"$PY" "$DEMO_ROOT/scripts/check_semantics.py"
```

Expected: PL and flow return to the approved values; six monthly oracles, total, filtered real gap and coverage pass. This is a local oracle demonstration; the historical baseline/candidate promotion gate is the next, separate evidence.

## 18–22 minutes — prove that the PR cannot hide the error

Open the already executed [PR #1](https://github.com/danielnrocha/cvm-fund-analytics/pull/1) and [compact negative report](../transform/evidence/pr-validation/negative.json). A +0.01 and -0.01 change on different days preserved monthly totals but the class/day comparison caught both differences. The check failed, GitHub blocked merge, and UAT stayed on the baseline. The restored final revision passed and merged without bypass.

Do not create a live regression in the public repository or wait for remote CI on stage. The full gate compares totals, months, class/day values and coverage, with identical frozen inputs. Intentional business changes need a reviewed baseline update; equality alone does not determine business truth.

## 22–25 minutes — history and questions

If time permits, open `models/history/sat_daily_report.sql` and `models/intermediate/current_daily.sql`. Show append-only capture identity, the replay anti-join, and the distinction between reporting date and capture timestamp. Existing integration evidence demonstrates corrections and A→B→A; avoid rebuilding that entire scenario live.

Close with the limits: minimal history satellite, not full Vault; semantic queries, not an evaluated AI agent; derived JSON envelope, not a native JSON source. Ask which business rule the audience would test next.

## Reset and recovery

Stop dbt/MetricFlow and the docs server. In a repository-root terminal:

```sh
make demo-reset
bash demo/rehearse.sh
```

Reset discards **all** edits and outputs inside the marked demo directory and restores the current repository project plus frozen baseline database. It never resets Git or changes original dev/UAT pointers. If a run fails halfway, inspect its real error; do not treat any nonzero exit as the intended red result. Reset provides the return to green.

## Offline fallback

Before the session, keep `demo/evidence/acceptance.json`, the compact negative PR report, and the locally saved rehearsal logs in `data/demo-rehearsals/` available. The restored project contains semantic CSVs in `evidence/` and generated docs in `target/`. Clearly label these as **previously executed evidence**, not live output. The baseline is already local; no new CVM downloads are needed. A local lineage table or screenshot is a fallback, not proof that the VS Code extension's lineage panel works.

`bash demo/rehearse.sh` automates the same edits for verification, with no hidden business calculations. Use the individual commands above during teaching so the audience sees the SQL, YAML and native test output.
