"""Chat completions client for an OpenAI-compatible API (Groq by default).

Every call has a timeout. Failures that may pass (rate limits, timeouts, 5xx, a malformed
tool call from the model) are retried with exponential backoff; when a model keeps failing,
the next configured model is tried; when all fail, `UpstreamError` reaches the API layer.

The rest of the app depends on the `ChatModel` protocol, so tests use a scripted fake.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from investigation_engine.core.config import Settings
from investigation_engine.core.errors import UpstreamError

log = structlog.get_logger()

# A chat message in the API's JSON shape: {"role": ..., "content": ..., ...}.
type Message = Mapping[str, object]

# Statuses worth retrying: rate limited, server-side failures, and Groq's 498 (capacity).
_RETRYABLE_STATUSES = frozenset({408, 429, 498, 500, 502, 503, 504})
# Groq rejects a tool call the model wrote as invalid JSON with 400 and this code; the
# model samples again on retry, so it usually succeeds.
_RETRYABLE_ERROR_CODES = frozenset({"tool_use_failed"})
_BACKOFF_BASE_S = 1.0
# A rate limit that lasts longer than this (e.g. a daily quota) won't pass by waiting:
# move on to the fallback model instead.
_MAX_RETRY_AFTER_S = 30.0


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    # JSON text exactly as the model wrote it; the tool's argument model validates it.
    arguments: str


@dataclass(frozen=True)
class Completion:
    content: str | None
    tool_calls: list[ToolCall]
    model: str
    total_tokens: int


class ChatModel(Protocol):
    async def complete(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[Mapping[str, object]] = (),
        force_tool: str | None = None,
    ) -> Completion:
        """One completion. `force_tool` makes the model call that tool; with tools but no
        `force_tool`, it must call one of them."""
        ...


def system_message(content: str) -> Message:
    return {"role": "system", "content": content}


def user_message(content: str) -> Message:
    return {"role": "user", "content": content}


def assistant_message(completion: Completion) -> Message:
    """The model's turn, replayed in the history so its tool calls match their results."""
    message: dict[str, object] = {"role": "assistant", "content": completion.content or ""}
    if completion.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in completion.tool_calls
        ]
    return message


def tool_message(call_id: str, content: str) -> Message:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


class _ModelFailedError(Exception):
    """One model failed for good; the client may still try the next one."""


# Just the parts of the API's response the app reads.
class _FunctionCall(BaseModel):
    name: str
    arguments: str


class _ToolCallPayload(BaseModel):
    id: str
    function: _FunctionCall


class _MessagePayload(BaseModel):
    content: str | None = None
    tool_calls: list[_ToolCallPayload] | None = None


class _Choice(BaseModel):
    message: _MessagePayload


class _Usage(BaseModel):
    total_tokens: int = 0


class _CompletionPayload(BaseModel):
    choices: list[_Choice]
    usage: _Usage = _Usage()


class LlmClient:
    @classmethod
    def from_settings(cls, settings: Settings) -> "LlmClient":
        if settings.llm_api_key is None:
            raise ValueError("LLM_API_KEY is not set.")
        models = [settings.llm_model]
        if settings.llm_fallback_model:
            models.append(settings.llm_fallback_model)
        return cls(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            models=models,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
        )

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        models: Sequence[str],
        timeout_s: float,
        max_retries: int,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """`transport` and `sleep` are for tests: a fake API and no real waiting."""
        if not models:
            raise ValueError("At least one model is required.")
        self._models = list(models)
        self._max_retries = max_retries
        self._sleep = sleep
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_s,
            transport=transport,
        )

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[Mapping[str, object]] = (),
        force_tool: str | None = None,
    ) -> Completion:
        body: dict[str, object] = {"messages": list(messages)}
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = (
                {"type": "function", "function": {"name": force_tool}} if force_tool else "required"
            )

        for model in self._models:
            try:
                return await self._complete_with_retries(model, body)
            except _ModelFailedError as error:
                log.warning("llm_model_failed", model=model, reason=str(error))
        raise UpstreamError("The language model is unavailable. Please try again in a minute.")

    async def close(self) -> None:
        await self._http.aclose()

    async def _complete_with_retries(self, model: str, body: dict[str, object]) -> Completion:
        for attempt in range(self._max_retries + 1):
            retry_after: float | None = None
            try:
                response = await self._http.post("/chat/completions", json={**body, "model": model})
            except httpx.TransportError as error:  # timeouts and connection failures
                reason = f"{type(error).__name__}"
            else:
                if response.status_code == httpx.codes.OK:
                    return _parse_completion(response, model)
                if not _is_retryable(response):
                    raise _ModelFailedError(f"HTTP {response.status_code}: {response.text[:200]}")
                reason = f"HTTP {response.status_code}: {response.text[:200]}"
                retry_after = _retry_after_seconds(response)
                if retry_after is not None and retry_after > _MAX_RETRY_AFTER_S:
                    raise _ModelFailedError(f"rate limited for {retry_after:.0f} s")

            if attempt == self._max_retries:
                raise _ModelFailedError(f"{reason} after {attempt + 1} attempts")
            # Jitter spreads retries out, so parallel requests don't all retry at once.
            delay = retry_after or _BACKOFF_BASE_S * 2**attempt * random.uniform(0.5, 1.5)
            log.info("llm_retry", model=model, attempt=attempt + 1, reason=reason, delay_s=delay)
            await self._sleep(delay)
        raise AssertionError("unreachable")  # the loop always returns or raises


def _is_retryable(response: httpx.Response) -> bool:
    if response.status_code in _RETRYABLE_STATUSES:
        return True
    try:
        code = response.json().get("error", {}).get("code")
    except ValueError:
        return False
    return code in _RETRYABLE_ERROR_CODES


def _retry_after_seconds(response: httpx.Response) -> float | None:
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def _parse_completion(response: httpx.Response, model: str) -> Completion:
    try:
        payload = _CompletionPayload.model_validate_json(response.content)
    except ValidationError as error:
        raise _ModelFailedError("unexpected response shape") from error
    if not payload.choices:
        raise _ModelFailedError("response has no choices")
    message = payload.choices[0].message
    return Completion(
        content=message.content,
        tool_calls=[
            ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
            for call in message.tool_calls or []
        ],
        model=model,
        total_tokens=payload.usage.total_tokens,
    )
