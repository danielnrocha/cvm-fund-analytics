# Codex CLI compatibility evidence

The local planner requires a structured response and a runtime that rejects tool calls. **Codex CLI 0.145.0 failed that boundary** in a historical loopback test. The CLI accepted and executed an unsolicited `update_plan` call even though the text-only model catalog configuration advertised no tools. The call updated an internal checklist. The experiment did not demonstrate filesystem or shell access with the text-only configuration.

| Loopback test | Observed result |
| --- | --- |
| Restricted flags, no catalog override | The Responses request advertised `update_plan`, `request_user_input`, and `view_image`. |
| Same flags with a text-only model catalog | The request omitted `tools` and retained `tool_choice: "auto"`. |
| Unsolicited `update_plan` | `Plan updated` |
| Unsolicited `view_image` | `view_image is not allowed because you do not support image inputs` |
| Unsolicited `exec_command` | `unsupported call: exec_command` |

The historical probe sent a strict JSON Schema requiring one boolean property named `ok`, with additional properties disallowed. The loopback provider supplied `{"ok":true}` and the CLI emitted it. No authenticated inference was attempted. Authenticated request limits, output, and latency remain unmeasured.

The historical implementation replaced the CLI home environment. A follow-up preserved the existing home environment, used the documented ephemeral credential store, stripped credential and endpoint overrides from the subprocess environment, and accepted only a dummy bearer credential at the loopback server. All three wire invocations hit their 15-second subprocess deadline. The executable probe was retired. The historical result is evidence of a compatibility blocker in the tested setup. [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) · [CLI 0.145.0 auth loader](https://github.com/openai/codex/blob/1635de866c61d1b76e50b31928ee6d61482435a8/codex-rs/login/src/auth/manager.rs)
