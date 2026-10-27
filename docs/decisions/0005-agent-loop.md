# ADR-0005: Plan, then a bounded tool-calling loop

**Status:** accepted · 2026-10-27

## Context

Multi-hop questions ("who was on call when INC-0412 started?") need a fact from one document
to find the next. One search with the question can't do that: Recall@2 stays near 0.61 for
every search configuration in [ADR-0003](0003-hybrid-search-rrf.md). The free LLM tier allows
about 200k tokens a day, so each question must have a known worst-case cost.

## Decision

`apps/api/src/investigation_engine/investigation/agent.py`:

1. **Plan:** a forced `plan_investigation` call splits the question into 1–4 searches.
2. **Search** each one with hybrid search, in parallel.
3. **Loop**, at most 4 LLM turns, with the tools `search_documents`, `get_document` and
   `submit_answer`. The last turn offers only `submit_answer`, so a question costs at most
   5 LLM calls.
4. **Verify** in code ([ADR-0006](0006-verified-citations.md)).

`Investigator(plan=False, max_turns=1)` is single-shot RAG, the baseline the evaluation
compares against, with the same prompts, tools and verification.

## Alternatives considered

- **Single-shot RAG:** cheaper (about half the tokens), measured as the baseline.
- **An unbounded ReAct loop:** better on long chains, but cost and latency have no ceiling.
- **A multi-agent setup** (planner, researcher, critic as separate agents): several times
  the tokens, which the free tier can't pay for.

## Evidence

The answer evaluation in [`docs/evaluation-report.md`](../evaluation-report.md) (agent vs
single-shot, section 6). Behaviour is pinned by `apps/api/tests/investigation/test_agent.py`.

## Consequences

A chain longer than the turn budget gets an incomplete answer or an abstention; the
evaluation's failure analysis shows where that happens.
