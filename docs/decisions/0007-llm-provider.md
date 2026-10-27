# ADR-0007: An OpenAI-compatible client on Groq's free tier, with a fallback model

**Status:** accepted · 2026-10-27

## Context

The demo must run for free with tool calling. Free LLM tiers have small, different quotas,
and they fail: 429 rate limits, 5xx, malformed tool calls.

## Decision

- One client for any OpenAI-compatible chat API
  (`apps/api/src/investigation_engine/llm/client.py`), Groq by default.
- Models: `openai/gpt-oss-120b`, falling back to `openai/gpt-oss-20b` when the main one keeps
  failing (each has its own daily quota).
- Errors: timeouts; retries on 408, 429, 5xx and failed tool calls with capped exponential
  backoff and jitter; `Retry-After` is honoured up to 30 s, beyond which the next model is
  tried; final failure is a 502 with a readable message.
- The evaluation judge is `qwen/qwen3.8-27b`, another model family, so the judge doesn't
  grade its own family's answers.

## Alternatives considered

| Provider | Why not |
|---|---|
| Gemini free tier | The quota ran out after a handful of agent calls |
| Cerebras | Needs a payment card |
| AWS Bedrock | New accounts start with a quota of 0 for gpt-oss; raising it takes a support case |
| Anthropic / OpenAI APIs | No free tier |

## Evidence

`apps/api/tests/llm/test_client.py`: retries after the server's delay, growing and capped
backoff, malformed tool calls, the fallback model, no retry on a client error, and a list
shaped error body. Switching provider is configuration only (`LLM_BASE_URL`, `LLM_MODEL`).

## Consequences

About 200k tokens per model per day: roughly 45 investigations. The evaluation runs over
more than one day (it is resumable), and the API caps investigations per day
(`apps/api/src/investigation_engine/core/rate_limit.py`).
