import asyncio
import json
import time

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from agent.planner import PlannerError, plan, run_decision


@pytest.fixture(autouse=True)
def disable_live_models(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


def test_native_output_repair_is_bounded_and_drops_bad_response():
    attempts = []
    accepted = {"decision": {"action": "clarify", "reason": "missing_period", "missing_slots": ["period"]}}

    def model(messages, info):
        assert info.model_request_parameters.output_mode == "native"
        assert info.function_tools == info.output_tools == []
        assert not info.model_request_parameters.native_tools
        attempts.append(str(messages))
        content = "unsafe secret raw output" if len(attempts) == 1 else json.dumps(accepted)
        return ModelResponse(parts=[TextPart(content)])

    outcome = asyncio.run(plan(FunctionModel(model), "Qual o PL?", {}, deadline=time.monotonic() + 2))
    assert outcome.attempts == 2
    assert outcome.decision.model_dump() == accepted["decision"]
    assert "unsafe secret raw output" not in attempts[1]


def test_invalid_output_stops_after_two_calls():
    calls = []

    def model(messages, info):
        calls.append(messages)
        return ModelResponse(parts=[TextPart("invalid")])

    with pytest.raises(PlannerError, match="invalid_model_output"):
        asyncio.run(plan(FunctionModel(model), "PL", {}, deadline=time.monotonic() + 2))
    assert len(calls) == 2


def test_shared_deadline_is_passed_to_gateway():
    from agent.contracts import QueryIntent

    intent = QueryIntent(action="query", metrics=["net_flow"], start_date="2026-04-01",
                         end_date="2026-04-30", grain="total", dimensions=[], filters=[], presentation="table")
    deadline = time.monotonic() + 2

    class Gateway:
        def query_metrics(self, received, *, deadline):
            assert received == intent
            return deadline

    assert run_decision(Gateway(), intent, deadline=deadline) == deadline


@pytest.mark.parametrize(("status", "code"), [
    (200, None), (400, "provider_http_400"), (500, "provider_http_500"), (401, "provider_unauthorized"),
])
def test_codex_wire_has_no_tools_or_http_retries(monkeypatch, tmp_path, status, code):
    import httpx2
    from pydantic_ai.providers.openai_codex import OpenAICodexCredentials

    from agent.auth import CredentialStore
    from agent.planner import codex_model

    requests = []
    async_client = httpx2.AsyncClient

    async def handle(request):
        requests.append(request)
        if status != 200:
            return httpx2.Response(status, json={"error": "untrusted raw response secret"})
        text = json.dumps({"decision": {"action": "clarify", "reason": "missing_period",
                                       "missing_slots": ["period"]}})
        part = {"type": "output_text", "text": text, "annotations": []}
        message = {"type": "message", "id": "msg_mock", "role": "assistant",
                   "status": "completed", "content": [part]}
        response = {"id": "resp_mock", "object": "response", "created_at": 1, "model": "gpt-6-luna",
                    "status": "completed", "output": [message],
                    "usage": {"input_tokens": 20, "output_tokens": 20, "total_tokens": 40,
                              "input_tokens_details": {"cached_tokens": 0},
                              "output_tokens_details": {"reasoning_tokens": 0}}}
        events = [
            {"type": "response.output_text.delta", "item_id": "msg_mock", "output_index": 0,
             "content_index": 0, "delta": text, "sequence_number": 0},
            {"type": "response.completed", "response": response, "sequence_number": 1},
        ]
        stream = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
        return httpx2.Response(200, text=stream, headers={"content-type": "text/event-stream"})

    class MockClient(async_client):
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False
            super().__init__(transport=httpx2.MockTransport(handle), **kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", MockClient)
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)  # MockTransport handles every request.
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-key")
    monkeypatch.setenv("OPENAI_ORG_ID", "ambient-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "ambient-project")
    store = CredentialStore(tmp_path / "private")

    async def run():
        with store.session():
            await store.save(OpenAICodexCredentials(access_token="fake", refresh_token="fake", account_id="fake"))
        async with codex_model(store) as model:
            return await plan(model, "Qual o PL?", {}, deadline=time.monotonic() + 2)

    if code is None:
        outcome = asyncio.run(run())
        assert outcome.decision.action == "clarify"
        assert outcome.attempts == 1
    else:
        with pytest.raises(PlannerError, match=f"^{code}$"):
            asyncio.run(run())
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://chatgpt.com/backend-api/codex/responses"
    assert request.headers["authorization"] == "Bearer fake"
    assert "openai-organization" not in request.headers
    assert "openai-project" not in request.headers
    body = json.loads(request.content)
    assert not body.get("tools")
    assert body["model"] == "gpt-6-luna"
    assert body["stream"] is True
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert "max_output_tokens" not in body


def test_provider_reported_token_limit_does_not_trigger_repair():
    from pydantic_ai.usage import RequestUsage

    calls = []

    def model(messages, info):
        calls.append(messages)
        return ModelResponse(parts=[TextPart("invalid")], usage=RequestUsage(output_tokens=5000))

    with pytest.raises(PlannerError, match="model_output_limit"):
        asyncio.run(plan(FunctionModel(model), "PL", {}, deadline=time.monotonic() + 2))
    assert len(calls) == 1
