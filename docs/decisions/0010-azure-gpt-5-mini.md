# ADR-0010: Evaluate and serve the agent with gpt-5-mini on Azure

**Status:** accepted · 2026-10-27. Supersedes the provider and model choice in
[ADR-0007](0007-llm-provider.md); its client design (OpenAI-compatible API, retries,
fallback, `UpstreamError`) stands.

## Context

The first answer run on Groq's free tier stopped at 35 of 45 questions: `openai/gpt-oss-120b`
allows about 200k tokens per day, an agent question uses about 4k, and three configurations
need several times the daily quota. A paid Groq tier wasn't available to new accounts, and
Amazon Bedrock starts new accounts at a quota of 0 for both gpt-oss and Claude (an increase
request went to AWS Support). Azure for Students includes $100 of credit with no card.

## Decision

- The agent runs on **`gpt-5-mini`** (a Global Standard deployment in Azure AI Foundry,
  Germany West Central), through the same client: only `LLM_BASE_URL`, `LLM_API_KEY` and
  `LLM_MODEL` changed, and `LLM_FALLBACK_MODEL` is empty because the Groq fallback doesn't
  exist on Azure.
- The judge stays **`qwen/qwen3.8-27b` on Groq**, still a different model family from the
  agent's.
- The partial gpt-oss-120b run is kept in `docs/evaluation/answers-gpt-oss-120b/` and compared
  with gpt-5-mini on the questions both answered.

## Alternatives considered

| Option | Why not |
|---|---|
| Stay on Groq, spread the run over three days | Misses the deadline for the cross-check run |
| `gpt-oss-120b` on Azure | Only offered there as a Hugging Face model on managed GPUs, which a student subscription can't rent |
| Claude Haiku 4.5 on Bedrock | Quota 0 pending AWS Support; needs a second client (Converse API) |
| A larger Azure model (`gpt-5`, `gpt-5.4`) | Several times the cost per question for a comparison that is about the loop, not the model |

## Evidence

- Changing provider took configuration only, no code: the protocol boundary from
  [ADR-0001](0001-modular-monolith.md) held.
- Tested before the switch: plain completion and a forced `plan_investigation` tool call.
- Cost: about 8k tokens per agent question; the whole evaluation is a few dollars of credit.
- Results: [`docs/evaluation-report.md`](../evaluation-report.md), section 6.

## Consequences

Answers now depend on a paid (credit-funded) deployment; when the credit runs out the demo
needs another key. The model comparison mixes providers as well as models, which the report
states.
