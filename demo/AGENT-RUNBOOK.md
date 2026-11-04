# Local analytics agent demo

The deterministic path is available for rehearsal. The natural-language path is experimental and requires separate model acceptance. This session is an optional extension to the [dbt presentation](RUNBOOK.md).

## Prepare once

Run these commands from the repository root. Dependency installation and the public baseline fetch need internet. The baseline fetch verifies the archive against the committed SHA-256 lock and refuses to replace an existing destination.

```sh
make setup          # separate dbt and MetricFlow environments
make setup-agent    # third Python 3.12 environment, installed with hashes
make fetch-baseline # first-time restore to baseline/releases
make test-agent     # controlled planner, mocked transport and real local MetricFlow
```

If the baseline is already present, start with `make agent-health` to verify its identity. Credential status checks the local file only. VS Code tasks can install agent dependencies, run the required suite, verify the release, and run the deterministic demo. Use the repository workspace for these tasks and keep any disposable dbt exercise in its dedicated terminal.

## Demonstrate the business contract offline

Ask: “What was the reported net worth at the end of September, and how much net cash entered this cohort from April through September?”

Open [the typed plan](agent-plan.json) and run:

```sh
make agent-demo
```

The CLI labels this **deterministic plan file** execution. It checks the sealed snapshot, validates the supplied Decision and executes a real MetricFlow query without a provider session. Expect closing PL **119385193058.06 BRL** with **60/60** closing coverage and interval net flow **4725910556.15 BRL** with **7554/7560** interval coverage. Explain that PL is a stock at one common closing date and net flow accumulates across dates. The fixed cohort has 60 reporting classes. The terminal shows release and query provenance and the verified executed SQL.

Files to show in VS Code include [the semantic definitions](../transform/models/marts/semantic.yml), [the intent contract](../agent/contracts.py), [the gateway](../agent/gateway.py) and [the evaluation contract](../specs/ai-agent-evals.md). The official dbt extension remains the dbt development interface. The agent runs in the terminal as a separate CLI.

## Rehearse the experimental natural-language path

Run login once if the application credential is absent. Open the emitted URL in the integrated browser while the command listens on localhost. Treat the authorization URL as private. This uses application-owned OAuth and the presenter's existing Codex subscription and quota. The question and approved capability catalog go to the provider over HTTPS. The database and query output stay local.

```sh
.venv-agent/bin/python -m agent.auth status
.venv-agent/bin/python -m agent.auth login
make agent-health

cvm_agent() {
  .venv-agent/bin/python -m agent.cli \
    --release-root baseline/releases \
    --release-id "$(compatibility/dbt-v2-metricflow/.venv-mf/bin/python -c 'import json; print(json.load(open("ci/baseline.lock.json"))["release_id"])')" \
    --mf compatibility/dbt-v2-metricflow/.venv-mf/bin/mf "$@"
}

cvm_agent ask --plan-only 'Mostre o PL no fechamento e o fluxo líquido total entre abril e setembro de 2026.'
cvm_agent ask --explain 'Mostre o PL no fechamento e o fluxo líquido total entre abril e setembro de 2026.'
cvm_agent ask 'Mostre PL e fluxo líquido por mês de abril a setembro de 2026.'
cvm_agent ask 'Qual o PL?'
cvm_agent ask 'Qual a rentabilidade da coorte em setembro de 2026?'
```

The first two commands send independent model requests. Show the structured decision in the first and inspect the verified SQL and provenance from the executed request in the second. Verify the six monthly rows and explain why monthly PL values cannot be summed into the interval total. The final two questions illustrate the intended clarification and refusal behaviors. Every invocation starts independently. Include dates and filters in each query. A19-style follow-ups remain outside the implemented single-turn scope.

If the experimental planner or subscription is unavailable, use the visibly labeled `make agent-demo` path for the presentation.

## Reset and evidence

Each agent invocation starts a new process and pins the verified release. Re-run `make agent-demo` to repeat the deterministic sequence. The agent uses disposable worker directories and creates no mutable demo project. For the separate dbt exercise, `make demo-reset` rebuilds the marked disposable workspace from the verified baseline. Neither demo command manages application OAuth.

The [implementation report](../reviews/agent-planner-implementation.md) separates deterministic gateway and transport checks from live canaries. The reviewed holdout, hidden-value end-to-end fixtures, multi-turn qualification and operational evidence remain acceptance gates. Per-PR CI uses the remote network-disabled runner, no OAuth and no model inference.
