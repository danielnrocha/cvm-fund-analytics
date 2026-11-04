# Local analytics agent: stack decision research

Research date: **2026-10-28**. Status: recommendation, not an executed model benchmark or an approved implementation. The machine inspected is an Apple M4 Pro, 12 CPU cores, **24 GB unified memory**. No models were downloaded, no inference was run, and no paid APIs were called.

## Decision

Recommend **Python 3.12 + Pydantic AI (slim) + local Ollama + Qwen3.5 4B Q4_K_M**, using a single structured planning call and a deterministic MetricFlow gateway. Benchmark Qwen3.5 9B as the quality challenger. Select the smallest candidate that passes the same business, safety, and latency gates; parameter count and vendor leaderboards do not establish the winner.

Keep dbt v2 and MetricFlow in their existing separate environments. Add a third, isolated agent environment only during implementation. The agent invokes the pinned MetricFlow executable through a controlled worker; do not install the agent framework into `.venv-mf` or upgrade the data stack for it. No local Docker, required paid service, vector database, autonomous SQL agent, multi-agent team, or hosted tracing service.

This recommendation optimizes the project's free, local, reproducible demo requirement. If laptop responsiveness were the sole priority, a small hosted API would be preferable: inference then consumes little local memory. Those are different objectives.

## Models and cost

Sizes below are the listed Ollama artifacts for the llama.cpp variant at research time, **not peak RAM estimates**. Mutable tags must be replaced by recorded artifact digests and a pinned runtime/backend before acceptance. Context, caches, GPU allocations, runtime, macOS and other applications need additional memory.

| Candidate | Listed artifact | Why consider it | Tradeoff / decision |
|---|---:|---|---|
| [Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b), Q4_K_M | 3.3 GB | Small enough to be the first constrained-planning experiment; tools and structured inference available in the surrounding stack | First candidate; PT/EN accuracy and ambiguous dates must be measured, not assumed |
| [Qwen3.5 9B](https://ollama.com/library/qwen3.5:9b), Q4_K_M | 6.6 GB | Quality challenger within a plausible 24 GB laptop budget | Extra memory and latency; promote only for measured correctness gain that still meets the demo SLO |
| [Gemma 4 E4B](https://ollama.com/library/gemma4:e4b), Q4_K_M | 6.6 GB | Alternative model family if Qwen fails the task | “Effective 4B” is not a 4 GB RAM promise; test later, not a third mandatory download |
| [gpt-oss 20B](https://ollama.com/library/gpt-oss:20b), MXFP4 | 14 GB | Open-weight reasoning/tool-use alternative | Poor first choice with 24 GB shared memory and other demo apps; active MoE parameters do not remove resident-weight costs |
| [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/pricing) | Hosted | Free tier can provide an optional external comparison, with little Mac inference load | Quotas, network, account eligibility and free-tier data-use policy; never a silent fallback |
| [Claude Haiku 5.5](https://platform.claude.com/docs/en/about-claude/pricing) | Hosted | Optional paid low-cost reference for structured planning | Violates a strictly zero-paid-call run; disabled unless user explicitly selects a paid experiment |

The Ollama catalog also lists MLX variants with different sizes. Comparing a 3.3 GB GGUF artifact with a 4.0 GB MLX artifact does not isolate runtime performance. Match model, quantization, context, decoding settings and workload when testing runtimes. [Qwen's model card](https://huggingface.co/Qwen/Qwen3.5-4B) is the primary source for the model; benchmark claims there are not CVM evaluation results.

At the research date, standard Gemini 3.5 Flash-Lite pricing is $0.30 / million input tokens and $2.50 / million output tokens, with a listed free tier. The free tier marks content as used to improve products; paid standard marks it otherwise. Claude Haiku 5.5 lists $0.10 input and $0.50 output per million for prompts up to 100,000 tokens. Verify availability and prices before any experiment. Sources: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing), [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

Illustrative budget, not measured usage: 4,000 input + 500 output tokens per question, one call, no cache, tools, taxes or retries. Gemini: $0.00245/question, $2.45/1,000; Haiku: $0.00065/question, $0.65/1,000. Actual billed reasoning/output and repair calls count. Local inference has zero provider token charges, but still consumes energy, storage, memory, and setup time. A 360-run eval at that illustrative budget costs $0.882 or $0.234 respectively; optional API spending must have an application-enforced cap, never depend only on a billing alert.

Do not claim a chat subscription grants arbitrary API access. The baseline needs no cloud credentials. Public CVM data does not imply the user's questions or local file paths are suitable for transmission.

## Runtime choice

| Option | Benefit | Cost / boundary | Decision |
|---|---|---|---|
| Ollama local | Model management and a local API; schema-constrained responses; usable on Mac and Linux | Additional daemon; pin backend because support differs across model/runtime variants | Baseline, one resident model, loopback only |
| MLX directly | Apple-oriented inference/quantization; useful performance experiment | Apple-specific; schema/tool compatibility needs its own probe and maintenance | Benchmark only if the baseline misses performance targets |
| LM Studio | GUI for loading models; GGUF/MLX and local APIs | Another desktop workflow to maintain for a VS Code-focused demo | Valid alternative if manual model management is preferred |

Sources: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [API compatibility](https://docs.ollama.com/api/openai-compatibility), [MLX LM](https://github.com/ml-explore/mlx-lm), [LM Studio](https://lmstudio.ai/docs/app). No runtime is declared faster on this Mac without a matched benchmark.

Initial benchmark configuration: text only, 8,192-token context, one inference at a time, one loaded model, at most 512 generated tokens for the plan, thinking disabled where the pinned model/runtime supports it. Reject context overflow rather than silently truncating business rules. Test 4,096 context only if the complete catalog, schema and question fit. Start with a fixed low-variance decoding configuration; evaluate repetitions because a fixed seed or temperature is not an exact reproducibility guarantee.

Targets, not measurements: warm end-to-end p95 <=15 seconds, cold p95 <=30 seconds, at least 30 representative warm requests plus 5 cold starts, zero timeouts in acceptance. Measure time-to-first-token, plan completion, MetricFlow execution, process-tree memory, GPU/unified-memory use, compression, swap growth and disk writes. Tokens/second alone is not the product SLO.

The preflight should show normal memory pressure with VS Code and the presentation apps open. Require >=15 GiB free **after** model installation, no sustained swap growth above 1 GiB over the short warm benchmark, and stop on pressure warnings or UI stalls. These are conservative project thresholds, not vendor hardware guarantees. Do not clear caches, kill apps, change macOS memory limits or download both candidates automatically. Local benchmark approval is separate from this design.

## Framework alternatives

| Approach | Strength | Tradeoff | Choice |
|---|---|---|---|
| Pydantic AI slim + Pydantic Evals | Typed intent/result contracts, output validation, bounded requests, testable model abstraction | Provider/schema compatibility still needs a real smoke test; framework guardrails are not authorization | Recommended |
| Plain Ollama SDK + Pydantic + pytest | Few dependencies; sufficient for a single structured call | We own provider adaptation, retries, trace consistency and evaluation plumbing | Escape hatch if framework integration adds complexity without benefit |
| LangGraph | Explicit state transitions, durable/resumable workflows, interrupts | More state/checkpoint machinery than a short read-only request needs | Reconsider for long workflows or actual human approval/resume requirements |

[Pydantic's Ollama integration](https://pydantic.dev/docs/ai/models/ollama/) documents `OllamaModel`, `OllamaProvider` and `NativeOutput`; the slim install uses its `openai` extra. `NativeOutput` constrains structure, not financial correctness. Verify this exact path on the chosen release rather than assuming all OpenAI-compatible APIs behave identically. [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/) can run without hosted Logfire. [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) is valuable when persistence and orchestration are actual requirements.

A full autonomous harness with shell/filesystem/code execution is intentionally excluded. Our planner does not need those permissions. Framework/runtime package versions will be selected and locked in the compatibility spike; this research does not invent an untested dependency lock.

## Why a small local gateway instead of official dbt MCP

[dbt's setup matrix](https://docs.getdbt.com/docs/dbt-ai/setup-local-mcp) distinguishes local CLI/LSP tools from Semantic Layer tools. The latter require platform variables and are not available without a platform account. Installing the MCP server locally is not equivalent to hosting MetricFlow's semantic API locally.

Use the existing local MetricFlow CLI behind a narrow typed boundary. The installed `mf query --help` confirms metrics, group-by, ISO date bounds, filters, CSV and explain options. It also confirms `--where` is SQL-like: therefore raw filters are prohibited. The renderer creates expressions only from validated catalog IDs and typed values. Shell argument arrays solve shell injection, not SQL/Jinja injection.

An optional future MCP facade can expose the same restricted gateway. It adds interoperability with assistants, not correctness or authorization. Do not expose dbt build, run, arbitrary SQL, profile selection or snapshot promotion to the analytics agent.

## Evidence and open gates

Already inspected: `transform/models/marts/semantic.yml`, `specs/metrics.md`, `scripts/check_semantics.py`, `release/snapshots.py`, `release/uat.py`, existing AI BI evaluation design and the installed CLI help. `release.uat.collect()` already demonstrates disposable project artifacts with a read-only snapshot. Reuse the pattern, not its unrestricted process environment unchanged.

Before implementation acceptance: native structured-output probe; exact version/model/backend pins; semantic catalog intersection for requested combinations; typed-filter injection tests; DuckDB external-access hardening compatibility; numerical precision preservation; independent design/security review; model quality and Mac benchmark. No compatibility, latency or model accuracy result is claimed here.

Related primary sources: [DuckDB security](https://www.duckdb.org/docs/current/operations_manual/securing_duckdb/overview), [Ollama concurrency and context](https://docs.ollama.com/faq), [Ollama cloud controls](https://github.com/ollama/ollama/blob/main/docs/cloud.mdx), [dbt semantic LLM benchmark](https://github.com/dbt-labs/dbt-llm-sl-bench). Benchmark methodology informs the eval design; its scores are not projected onto this project.

## Post-refactor sequencing

Main `c884ebc` preserves the metric contract and has passing remote acceptance. The next experiment is [Wizard qualification with deterministic Pydantic AI outputs](wizard-agent-spike.md), not an Ollama/model installation. The model recommendation above remains provisional; no hardware benchmark or language evaluation has been performed.
