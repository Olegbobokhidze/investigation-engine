# ADR-0006: Citations are checked in code; no valid citation means abstain

**Status:** accepted · 2026-10-27

## Context

An answer must be grounded in the documents. A prompt alone can't guarantee that: models
cite passage numbers they were never shown, or answer from their own knowledge.

## Decision

The model cites numbered passages as `[n]`. After it answers,
`apps/api/src/investigation_engine/investigation/citations.py`:

- removes citations to passages the model wasn't shown;
- turns an answer with no valid citation into `insufficient_evidence` (abstain);
- drops a reported conflict that doesn't cite both sides;
- renumbers sources 1..n for the UI.

While turns are left, an uncited answer is sent back with a request for citations rather
than discarded.

## Alternatives considered

- **Trust the prompt:** cheaper, but an invented `[7]` would reach the user.
- **An LLM verifier for every sentence:** checks meaning, not just numbers, but doubles the
  cost of every question.

## Evidence

- `apps/api/tests/investigation/test_citations.py` and
  `apps/api/tests/investigation/test_agent.py`.
- Citation precision and recall in [`docs/evaluation-report.md`](../evaluation-report.md),
  section 6.

## Consequences

The check is structural: a valid `[n]` attached to a claim the passage doesn't support
passes. The citation precision metric measures how often that matters.
