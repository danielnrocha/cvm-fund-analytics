"""Capture the Codex CLI's planner request using a dummy loopback provider."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread

MODEL = "gpt-6-luna"
PROMPT = 'Return the literal JSON {"ok":true}.'
SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
CONFIG = (
    "approval_policy=\"never\"",
    "project_doc_max_bytes=0",
    "web_search=\"disabled\"",
    "mcp_servers={}",
    "skills.bundled.enabled=false",
    "features.shell_tool=false",
    "features.apps=false",
    "features.hooks=false",
    "features.multi_agent=false",
    "features.multi_agent_v2=false",
    "features.skill_search=false",
    "features.skill_mcp_dependency_install=false",
    "features.tool_suggest=false",
    "features.image_generation=false",
    "features.in_app_browser=false",
)


def _run(root: Path, *, text_only: bool, calls: dict) -> tuple[list[dict], subprocess.CompletedProcess]:
    final = {
        "type": "message", "id": "message-1", "role": "assistant",
        "content": [{"type": "output_text", "text": '{"ok":true}'}],
    }
    requests = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            if self.path != "/v1/responses":
                self.send_error(404)
                return
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            items = [final]
            if calls and len(requests) == 1:
                items = [
                    {"type": "function_call", "call_id": name, "name": name,
                     "arguments": json.dumps(arguments)}
                    for name, arguments in calls.items()
                ]
            events = [
                {"type": "response.output_item.done", "item": item} for item in items
            ]
            events.append({
                "type": "response.completed",
                "response": {"id": f"response-{len(requests)}"},
            })
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for event in events:
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())

    codex = shutil.which("codex")
    if codex is None:
        raise RuntimeError("Codex CLI is required")
    home = root / "home"
    (home / ".codex").mkdir(parents=True)
    scratch = root / "scratch"
    scratch.mkdir()
    (root / "AGENTS.md").write_text("PROBE_INHERITED_INSTRUCTIONS")
    schema = root / "schema.json"
    schema.write_text(json.dumps(SCHEMA))
    environment = {
        "HOME": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "PATH": "/usr/bin:/bin",
        "PROBE_DUMMY_KEY": "probe-dummy-credential",
    }
    overrides = CONFIG
    if text_only:
        bundled = subprocess.run(
            [codex, "debug", "models", "--bundled"], cwd=scratch, env=environment,
            stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=10,
        )
        template = json.loads(bundled.stdout)["models"][0]
        # Retain version-specific schema while explicitly stripping optional tools.
        model = {
            **template,
            "slug": MODEL,
            "input_modalities": ["text"],
            "shell_type": "disabled",
            "apply_patch_tool_type": None,
            "experimental_supported_tools": [],
            "base_instructions": "",
            "model_messages": None,
        }
        catalog = root / "catalog.json"
        catalog.write_text(json.dumps({"models": [model]}))
        overrides += (f"model_catalog_json={json.dumps(str(catalog))}",)
    with HTTPServer(("127.0.0.1", 0), Provider) as server:
        provider_config = (
            'model_provider="loopback"',
            'model_providers.loopback.name="Probe loopback"',
            f'model_providers.loopback.base_url="http://127.0.0.1:{server.server_port}/v1"',
            'model_providers.loopback.wire_api="responses"',
            'model_providers.loopback.env_key="PROBE_DUMMY_KEY"',
            'model_providers.loopback.request_max_retries=0',
            'model_providers.loopback.stream_max_retries=0',
        )
        command = [
            codex, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
            "--skip-git-repo-check", "--strict-config", "--sandbox", "read-only", "--model", MODEL,
            "--output-schema", str(schema),
        ]
        for override in overrides + provider_config:
            command.extend(("-c", override))
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            result = subprocess.run(
                [*command, PROMPT],
                cwd=scratch,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=15,
            )
        finally:
            server.shutdown()
            worker.join()
    expected_requests = 2 if calls else 1
    if result.returncode != 0 or len(requests) != expected_requests:
        raise RuntimeError(
            f"CLI exited {result.returncode} after {len(requests)} requests. {result.stderr[-1500:]}"
        )
    return requests, result


def capture(root: Path, *, text_only: bool = False) -> dict:
    requests, _ = _run(root, text_only=text_only, calls={})
    return requests[0]


def challenge(root: Path) -> tuple[dict, dict]:
    requests, result = _run(root, text_only=True, calls={
        "update_plan": {"plan": [{"step": "sentinel", "status": "completed"}]},
        "view_image": {"path": "sentinel.png"},
        "exec_command": {"cmd": "printf PROBE_SHELL_EXECUTED"},
    })
    outputs = {
        item["call_id"]: item["output"]
        for item in requests[1]["input"]
        if item["type"] == "function_call_output"
    }
    return outputs, json.loads(result.stdout)


if __name__ == "__main__":
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        for label in ("baseline", "text-only", "challenge"):
            (root / label).mkdir()
        baseline = capture(root / "baseline")
        text_only = capture(root / "text-only", text_only=True)
        outputs, final = challenge(root / "challenge")
    tool_specs = text_only.get("tools", [])
    # Unknown tool responses also fail the compatibility gate.
    rejected = (
        set(outputs) == {"update_plan", "view_image", "exec_command"}
        and all(
            isinstance(output, str)
            and ("unsupported" in output.lower() or "is not allowed" in output.lower())
            for output in outputs.values()
        )
    )
    compatible = not tool_specs and rejected and final == {"ok": True}
    print(json.dumps({
        "status": "PASS" if compatible else "BLOCKED",
        "model": text_only["model"],
        "baseline_tool_specs": [spec["name"] for spec in baseline["tools"]],
        "text_only_tool_specs": tool_specs,
        "injected_tool_outputs": outputs,
        "synthetic_final_output": final,
    }, indent=2))
    raise SystemExit(0 if compatible else 1)
