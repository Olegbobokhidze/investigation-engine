import json
from collections.abc import Callable

import httpx
import pytest

from investigation_engine.core.errors import UpstreamError
from investigation_engine.llm.client import LlmClient, user_message

type Handler = Callable[[httpx.Request], httpx.Response]


def _ok(content: str = "ok", tool_calls: list[dict[str, object]] | None = None) -> httpx.Response:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return httpx.Response(
        200, json={"choices": [{"message": message}], "usage": {"total_tokens": 42}}
    )


class FakeApi:
    """Answers each request with the next scripted response and records what was sent."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    @property
    def models(self) -> list[object]:
        return [request["model"] for request in self.requests]


def _client(api: FakeApi, sleeps: list[float], models: tuple[str, ...] = ("main",)) -> LlmClient:
    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    return LlmClient(
        base_url="https://llm.test/v1",
        api_key="test-key",
        models=models,
        timeout_s=5,
        max_retries=2,
        transport=httpx.MockTransport(api),
        sleep=record_sleep,
    )


async def test_complete_parses_content_tool_calls_and_usage() -> None:
    api = FakeApi(
        _ok(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "search_documents", "arguments": '{"query": "x"}'},
                }
            ],
        )
    )

    completion = await _client(api, []).complete([user_message("Hi")])

    assert [(call.id, call.name, call.arguments) for call in completion.tool_calls] == [
        ("call_1", "search_documents", '{"query": "x"}')
    ]
    assert completion.model == "main"
    assert completion.total_tokens == 42


async def test_complete_forces_the_named_tool() -> None:
    api = FakeApi(_ok())
    tool = {"type": "function", "function": {"name": "plan", "parameters": {}}}

    await _client(api, []).complete([user_message("Hi")], tools=[tool], force_tool="plan")

    assert api.requests[0]["tool_choice"] == {"type": "function", "function": {"name": "plan"}}


async def test_complete_retries_a_rate_limit_after_the_servers_delay() -> None:
    api = FakeApi(httpx.Response(429, headers={"retry-after": "3"}), _ok())
    sleeps: list[float] = []

    completion = await _client(api, sleeps).complete([user_message("Hi")])

    assert completion.content == "ok"
    assert sleeps == [3.0]


async def test_complete_retries_timeouts_with_growing_backoff() -> None:
    api = FakeApi(httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"), _ok())
    sleeps: list[float] = []

    await _client(api, sleeps).complete([user_message("Hi")])

    # 1 s, then 2 s, each with ±50% jitter.
    assert len(sleeps) == 2
    assert 0.5 <= sleeps[0] <= 1.5
    assert 1.0 <= sleeps[1] <= 3.0


async def test_complete_retries_a_malformed_tool_call() -> None:
    api = FakeApi(httpx.Response(400, json={"error": {"code": "tool_use_failed"}}), _ok())

    completion = await _client(api, []).complete([user_message("Hi")])

    assert completion.content == "ok"


async def test_complete_switches_to_the_fallback_model_when_the_quota_is_used_up() -> None:
    api = FakeApi(httpx.Response(429, headers={"retry-after": "3600"}), _ok())
    sleeps: list[float] = []

    completion = await _client(api, sleeps, models=("main", "fallback")).complete(
        [user_message("Hi")]
    )

    assert completion.model == "fallback"
    assert api.models == ["main", "fallback"]
    assert sleeps == []


async def test_complete_does_not_retry_a_client_error() -> None:
    api = FakeApi(httpx.Response(401, json={"error": {"code": "invalid_api_key"}}), _ok())

    completion = await _client(api, [], models=("main", "fallback")).complete([user_message("Hi")])

    assert api.models == ["main", "fallback"]
    assert completion.model == "fallback"


async def test_complete_raises_upstream_error_when_every_model_fails() -> None:
    api = FakeApi(*[httpx.Response(503)] * 6)

    with pytest.raises(UpstreamError):
        await _client(api, [], models=("main", "fallback")).complete([user_message("Hi")])

    assert api.models == ["main"] * 3 + ["fallback"] * 3
