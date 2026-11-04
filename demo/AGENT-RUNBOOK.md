# Local analytics agent demo

Status: implementation in progress; natural-language model acceptance has not passed. Do not present controlled planner tests or plan-file execution as live AI. This is an optional extension to the existing [dbt presentation](RUNBOOK.md), not a replacement for its red/green exercises.

## Story and acceptance boundary

Start with the business question: **“What was the reported net worth at the end of September, and how much net cash entered this cohort from April through September?”**

Explain the difference before showing a result: PL is a stock at a common closing date, whereas net flow is accumulated over an interval. A language model must not choose new financial formulas or sum monthly balances. The fixed cohort contains 60 reporting classes; it is not the whole Brazilian fund industry.

The local model proposes a structured intent. Trusted Python validates the metric names, dates, grain and filters. MetricFlow owns the financial computation. The immutable approved DuckDB snapshot owns the data. The deterministic renderer owns the displayed numbers, coverage and provenance. No API-key billing, Wizard trial, local model or local Docker is part of this runtime. Codex uses the presenter’s existing subscription/credits and requires network access.

## What to open in VS Code

1. `transform/models/marts/semantic.yml`: common-cut PL and flow definitions.
2. `agent/contracts.py`: the allowed intent shape; there is no SQL or shell field.
3. `agent/catalog.py`: approved capabilities and published semantic binding.
4. `agent/gateway.py`: the read-only boundary and MetricFlow execution.
5. `specs/ai-agent-evals.md`: exact numeric and adversarial acceptance criteria.

The official dbt extension remains useful for SQL/model navigation and lineage. The analytics agent runs in the integrated terminal; it is not a Wizard feature.

## Demonstration sequence after acceptance

- Ask the business question with explicit dates. Show the interpreted plan before the answer.
- Check PL **119385193058.06 BRL** and net flow **4725910556.15 BRL**. Show separate closing and interval coverage; interval reporting is **7554/7560**, so do not describe the flow as fully reported.
- Request monthly output for the same explicit interval. Show six rows and explain why their PL values must not be summed into the interval total.
- Ask a PL question without dates. Show a clarification rather than an invented period.
- Ask for fund returns or the whole industry's assets. Show the capability/population restriction.
- Inspect the recorded SQL, release identity and semantic fingerprint behind a successful result.
- Explain the test split: deterministic boundary tests run in every PR; actual language-model accuracy and latency have a separate, version-bound report.

Runtime commands, measured model results and final rehearsal evidence will be added only after the CLI and acceptance gates are validated. The existing dbt demo remains independently runnable.
