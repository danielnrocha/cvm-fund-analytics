# Analytics agent acceptance evidence

Date: 2026-11-04. Natural-language acceptance is pending. This report distinguishes live subscription inference from deterministic tests. No local model, Docker, API key, billing activation or Wizard trial was used.

## Development iteration 1

The [first development run](agent-evidence/development-round1.json) used the original instructions at `8213826`, gpt-6-luna through the native Codex OAuth provider, and the sealed `cvm-linux-uat-v3` baseline. It made 72 inference requests with no repair and no holdout access. Results: 61/72 exact decisions, 32/33 supported queries, 47/57 critical cases, 32/33 numeric-oracle trials. A missed supported intent counts as a failed numeric trial; it is not evidence of an incorrectly calculated amount.

The empirical warm turn p50 was 2,440 ms, p95 6,023 ms and maximum 8,926 ms. Timing includes gateway execution for accepted queries and excludes initial release setup. This does not establish cold-start latency or production acceptance.

Failures were D06 PT/PT paraphrase (unqualified coverage), D11 all languages (relative month), D15 PT (population refusal reason), D16 EN (dimension refusal reason), D17 all languages (holdings refusal reason), and D23 PT (class grouping). The development evidence drove an instruction-only revision in `6b83774`; schema, gateway and expected answers were unchanged. The revised instructions distinguish ambiguity, relative dates, refusal reasons and reporting class versus classification. All nine planner boundary tests passed after that change. Development iteration 2 is recorded below.

## Evidence limits

Reports contain normalized decisions and hashes, not raw provider responses, reasoning, OAuth credentials or account identifiers. The `served_model` field is SDK-observed metadata and may retain the requested alias when provider metadata is absent. No immutable remote weights digest is available. Client response limits are not a server-side spending cap.

The 78-test deterministic agent suite and the 18-family/84-row real gateway replay are separate from model-quality denominators. Single-turn operation does not implement conversational follow-ups. Synthetic result-boundary fixtures do not establish end-to-end model acceptance over a changed sealed dataset. The updated remote CI, frozen holdout, operational acceptance and independent final review remain open.

## Development iteration 2

The [second development run](agent-evidence/development-round2.json) kept gpt-6-luna at low reasoning and used the revised instructions at `6b83774`. It made 72 requests without repairs: 69/72 exact, 30/33 supported queries and numeric trials, 55/57 critical cases. Warm p50 was 2,044 ms, p95 7,429 ms and maximum 11,683 ms. D22 PT/PT paraphrase and D23 PT paraphrase were false refusals or clarifications for supported explicit coverage queries. This candidate did not pass. A bounded development-only experiment raises reasoning effort before committing to the full acceptance run; no holdout data has been used.

## Bounded development experiments

- [Medium reasoning](agent-evidence/development-medium-focused.json), unchanged second instructions and gpt-6-luna, D22/D23 only: 4/6 exact/numeric. Greater reasoning did not resolve the development failures.
- [Stronger candidate availability](agent-evidence/development-sol-focused.json), gpt-6.1-sol at low reasoning, same six cases: six HTTP 503 failures. No successful response or reported token usage; this is availability evidence, not a quality comparison. There was no runtime fallback.
- [Third instruction revision](agent-evidence/development-policy3-focused.json), gpt-6-luna at low reasoning, D06/D22/D23: 9/9 exact, 6/6 supported/numeric, empirical p95 7,526 ms. Revision `1662135` explicitly separates approved filters from unsupported groupings and identifies unambiguous coverage terms. This is a targeted development check, not held-out acceptance. Full development repetition is pending.

## Remote deterministic gate

[GitHub Actions run 41911391800](https://github.com/danielnrocha/cvm-fund-analytics/actions/runs/41911391800) passed for `6b83774bf0df0c07c08506c66bbe63300b4b25e3`, including the semantic UAT gate and offline agent suite. Subsequent revisions require a fresh run before merge.
