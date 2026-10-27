# ADR-0003: Hybrid search fused with our weighted RRF, k=10

**Status:** accepted · 2026-10-26

## Context

Dense search finds paraphrases but misses rare names and ids (`CHG-2291`); BM25 is the
opposite. Their scores are on different scales, so they can't be added. The assignment asks
for at least one ranking or fusion algorithm of our own.

## Decision

Fetch the top 40 dense and top 40 BM25 chunks, then merge them with weighted Reciprocal Rank
Fusion, `score = Σ weight / (k + rank)`, written by us in
`apps/api/src/investigation_engine/retrieval/fusion.py`. Defaults: k=10, equal weights
(`RRF_K`, `RRF_DENSE_WEIGHT`, `RRF_SPARSE_WEIGHT`).

## Alternatives considered

- **Dense only / BM25 only:** the baselines below.
- **k=60**, the RRF paper's value, and **BM25 down-weighted** to 0.5: measured, both worse.
- **A cross-encoder reranker:** more accurate per query, but a second model in a 2 GB server
  and seconds of CPU per search.

## Evidence

[`docs/evaluation/retrieval-hotpotqa.md`](../evaluation/retrieval-hotpotqa.md), 200 HotpotQA
questions over all 66,581 paragraphs: k=10 reaches Recall@10 0.875 against 0.792 (dense) and
0.785 (BM25), and beats k=60 (0.855) on every metric. Tests:
`apps/api/tests/retrieval/test_fusion.py`.

## Consequences

k was tuned on those 200 questions, so the answer evaluation uses later questions nothing
was tuned on (`HOTPOTQA_OFFSET` in `apps/api/src/investigation_engine/evaluation/answers.py`).
