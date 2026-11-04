# Analytics agent acceptance evidence

Date: 2026-11-04. Natural-language acceptance is pending. This report distinguishes live subscription inference from deterministic tests. No local model, Docker, API key, billing activation or Wizard trial was used.

## Development iteration 1

The [first development run](agent-evidence/development-round1.json) used the original instructions at `8213826`, gpt-6-luna through the native Codex OAuth provider, and the sealed `cvm-linux-uat-v3` baseline. It made 72 inference requests with no repair and no holdout access. Results: 61/72 exact decisions, 32/33 supported queries, 47/57 critical cases, 32/33 numeric-oracle trials. A missed supported intent counts as a failed numeric trial; it is not evidence of an incorrectly calculated amount.

The empirical warm turn p50 was 2,440 ms, p95 6,023 ms and maximum 8,926 ms. Timing includes gateway execution for accepted queries and excludes initial release setup. This does not establish cold-start latency or production acceptance.

Failures were D06 PT/PT paraphrase (unqualified coverage), D11 all languages (relative month), D15 PT (population refusal reason), D16 EN (dimension refusal reason), D17 all languages (holdings refusal reason), and D23 PT (class grouping). The development evidence drove an instruction-only revision in `6b83774`; schema, gateway and expected answers were unchanged. The revised instructions distinguish ambiguity, relative dates, refusal reasons and reporting class versus classification. All nine planner boundary tests passed after that change. Development iteration 2 is pending.

## Evidence limits

Reports contain normalized decisions and hashes, not raw provider responses, reasoning, OAuth credentials or account identifiers. The `served_model` field is SDK-observed metadata and may retain the requested alias when provider metadata is absent. No immutable remote weights digest is available. Client response limits are not a server-side spending cap.

The 78-test deterministic agent suite and the 18-family/84-row real gateway replay are separate from model-quality denominators. Single-turn operation does not implement conversational follow-ups. Synthetic result-boundary fixtures do not establish end-to-end model acceptance over a changed sealed dataset. The updated remote CI, frozen holdout, operational acceptance and independent final review remain open.
