# ADR-0009: Cross-check an answer against other sources before accepting it

**Status:** proposed · 2026-10-27. Off by default (`AGENT_CROSS_CHECK=false`) until
`make eval-cross-check` shows it helps.

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

Pending: `make eval-cross-check` runs the 28 Northwind questions with the cross-check;
`make eval-report` compares it with the agent on the same questions (contradiction recall,
false conflict rate, tokens). Tests: `apps/api/tests/investigation/test_agent.py`.

## Consequences

If contradiction recall rises without more false conflicts, the default becomes `true` and
this ADR is accepted; if not, it is rejected and the result stays in the report.
