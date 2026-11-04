# Wizard access qualification

Verified: **2026-10-28**. Status: **documentation and local installation inspected; authenticated access and implementation canary pending**.

| Question | Evidence and result |
|---|---|
| Official extension installed? | Yes: local `dbtlabsinc.dbt-0.122.0` package and VS Code UI; dbt 2.0.9. |
| Wizard ready locally? | No executable found in PATH or common/documented install locations. Extension offers sign-in; authenticated execution not demonstrated. |
| Native Wizard chat available? | Package contributes `dbt.wizardSidebar`, gated by `dbt.wizardUiEnabled`; view not visible in inspected sidebar. Do not bypass hidden flags. |
| Permanently free? | No: documented free-account offer is a one-time trial, up to 30 days or USD 100, whichever comes first. |
| User eligible? | User has a domain but no dbt account. Signup eligibility and actual credits remain unverified. |
| Python/Pydantic AI and MetricFlow support? | CLI documents shell sandboxing, task execution and applying code diffs. Feasible in principle; no implementation canary executed. |

The documented local workflow is Wizard CLI alongside the official extension. A free extension does not imply free Wizard entitlement. For self-hosted projects, `dbt login` or `wizard login` opts into the trial and can create the free account. A business email is required; a domain alone does not prove eligibility. No credit card is required for the trial. Do not add payment details, activate paid usage, configure paid provider keys or download models during validation.

The user must complete signup/authentication and verify displayed trial status, expiry, available credits and absence of paid activation before model-backed work. No account was created or trial started during this inspection. Avoid using an employer account for a personal repository.

## Qualification canary after authentication

The executable acceptance design is now [wizard-agent-spike.md](wizard-agent-spike.md), reconciled with merged main `c884ebc`. The steps below are a summary; W01–W12 define pass/fail. A fresh PATH check still found no Wizard executable; account state has not been reauthenticated. The installed `dbt wizard` launcher can install the CLI, so do not invoke it during read-only inspection.

1. Inspect the official installer, install Wizard CLI, run `wizard doctor`, record version and health without tokens.
2. In the VS Code integrated terminal, request a read-only plan grounded in `AI-SPEC.md`, metric contracts and existing MetricFlow commands. Distinguish implementation assistant from analytics runtime.
3. In an isolated scratch directory, have Wizard write failing tests for unknown metrics and valid typed requests, then implement a minimal Pydantic AI-facing request boundary using a test model. Record dependency versions and test results. Mocks prove plumbing, not LLM quality; no model download needed.
4. Run a bounded MetricFlow integration probe against a pinned read-only snapshot. Preserve null/zero distinctions and reconcile PL **119385193058.06** and net flow **4725910556.15** with repository oracles. No rebuild or promotion.
5. Review the diff and negative tests for arbitrary SQL, shell injection, unknown metrics and unbounded requests. Mark suitability verified only after Python tests and real MetricFlow checks pass.

Trial credits fund the implementation assistant, not the future local analytics runtime. Continued Wizard usage after expiry is a separate decision. A failed canary can change the implementation assistant without changing the architecture.

## Sources

- [Trial and billing](https://docs.getdbt.com/docs/dbt-ai/pricing-billing/trial-and-billing)
- [Official extension](https://docs.getdbt.com/docs/about-dbt-extension)
- [CLI installation](https://docs.getdbt.com/docs/dbt-ai/wizard-cli)
- [CLI commands](https://docs.getdbt.com/docs/dbt-ai/wizard-cli-reference)

No billing activated, models downloaded, Docker executed or agent implemented during this validation.
