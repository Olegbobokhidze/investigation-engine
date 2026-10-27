# ADR-0009: Cross-check an answer against other sources before accepting it

**Status:** rejected · 2026-10-27, after measurement. The code stays, off by default
(`AGENT_CROSS_CHECK=false`), so the experiment can be rerun.

## Context

Contradictions are the agent's weakest question type. In the first answer run, the agent
often had both disagreeing passages and still gave only one value ("When was INC-0412
resolved?": 10:20 from the status page, not also 10:05 from the incident report). Once the
model has an answer, it stops looking for a second opinion.

## Decision

When the agent submits a cited answer, `_cross_check` in
`apps/api/src/investigation_engine/investigation/agent.py`:

1. searches once more with the answer's first sentence, its direct claim, which finds
   passages that state the same fact in other words or other numbers;
2. shows the model those passages and asks it (`CROSS_CHECK` in
   `apps/api/src/investigation_engine/investigation/prompts.py`) to compare every fact in
   its answer with every passage, then forces it to resubmit;
3. keeps the first answer if the resubmission is invalid, uncited or an abstention.

Cost: one search and one LLM call per answered question.

## Alternatives considered

- **A stronger prompt only:** already says to compare passages; the failures happened with
  that prompt.
- **A separate verifier model** that reads the answer and all passages: the same idea at
  higher cost, and a second model's quota.
- **Pairwise fact extraction and comparison in code:** precise for numbers and times, brittle
  for anything else.

## Evidence

`make eval-cross-check`, then `make eval-report`: on the 28 Northwind questions, against the
agent on the same questions ([`docs/evaluation-report.md`](../evaluation-report.md), section 6):

| | agent | agent + cross-check |
|---|---|---|
| Answer correctness | 0.82 | 0.75 |
| Contradiction recall | 0.83 | 0.83 |
| False conflict rate | 0.14 | 0.23 |
| Evidence recall | 0.85 | 0.97 |
| Tokens per question | 7,771 | 10,572 |

The extra search found the second source more often, but the forced comparison made the
model report conflicts on side facts instead of the one asked about. Tests:
`apps/api/tests/investigation/test_agent.py`.

## Consequences

Contradictions stay handled by the prompt rule and the agent's own follow-up searches,
which already reach 0.83 contradiction recall. A narrower check, comparing only the facts
the question asks about, is the next idea to measure.
