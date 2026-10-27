# ADR-0011: Re-rank the top fused candidates with a small cross-encoder

**Status:** rejected as the default · 2026-10-27, after measurement. The reranker stays as
an option (`RERANK_MODEL`), off by default.

## Context

Weighted RRF ([ADR-0003](0003-hybrid-search-rrf.md)) only combines positions; it never reads
the passages. Its first result was a gold paragraph for 88% of questions (MRR 0.880), and
both gold paragraphs were in the top 2 for only 62%. The agent reads 6 passages per search,
so what reaches the top of the list is what it reasons over.

## Decision

After fusion, a cross-encoder (`Xenova/ms-marco-MiniLM-L-6-v2`, 80 MB, ONNX on CPU through
fastembed) reads the question with each of the top 20 fused chunks and scores the pair;
the chunks are reordered by that score
(`apps/api/src/investigation_engine/retrieval/reranking.py`). It is a setting
(`RERANK_MODEL`, `RERANK_CANDIDATES`); empty turns it off.

The decision was to turn it on if the answers improved as well as retrieval. They didn't,
so it is off.

## Alternatives considered

- **No reranker:** the baseline below.
- **MiniLM-L-12 (120 MB):** within a point on every metric, twice the time.
- **`bge-reranker-base` (1 GB):** doesn't fit next to the embedding models on a 2 GB host.
- **An LLM as reranker:** one more LLM call per search, at the agent's 3–5 searches per
  question.

## Evidence

[`docs/evaluation/retrieval-hotpotqa.md`](../evaluation/retrieval-hotpotqa.md), 200 HotpotQA
questions over all 66,581 paragraphs:

| | RRF k=10 | + MiniLM-L-6 | + MiniLM-L-12 |
|---|---|---|---|
| Recall@2 | 0.615 | 0.665 | 0.680 |
| Recall@10 | 0.875 | 0.892 | 0.885 |
| MRR | 0.880 | 0.932 | 0.933 |
| Ranking time per search | < 1 ms | 1.1 s | 2.0 s |

The answer evaluation, rerun with the reranker on (`make eval-reranker`,
[`docs/evaluation-report.md`](../evaluation-report.md), section 6), 48 questions:

| | reranker off | reranker on |
|---|---|---|
| Agent: answer correctness | **0.79** | 0.69 |
| Agent: evidence recall | 0.88 | **0.91** |
| Single-shot: answer correctness | 0.67 | 0.67 |
| Single-shot: evidence recall | **0.85** | 0.82 |
| Agent latency, median | **21 s** | 22 s |

Of the 7 agent questions that turned wrong, 1 lost a gold paragraph to the new ranking; the
others failed in the answer step in ways earlier runs show too (over-caution, an invented
conflict, an answer to an unanswerable question) or were a judge error. So the drop is not
clearly caused by the reranker, but nothing shows it helps the answers either, and it adds
latency and 80 MB. Tests: `apps/api/tests/retrieval/test_reranking.py`,
`apps/api/tests/retrieval/test_search.py`.

## Consequences

A retrieval metric is a proxy: here it improved while the answers didn't, so the deployed
default follows the end-to-end measurement. A reranker trained on web search (MS MARCO) may
also judge short change-log and incident passages differently from Wikipedia paragraphs;
a domain test, or a larger reranker on a bigger host, is the next thing to measure.
