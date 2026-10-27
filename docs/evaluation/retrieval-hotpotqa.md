# Retrieval evaluation: HotpotQA

`make eval-retrieval` · raw numbers in [`retrieval-hotpotqa.json`](retrieval-hotpotqa.json)

## Setup

- **Corpus:** all 66,581 distinct paragraphs of the HotpotQA dev distractor set, plus the 12
  Northwind Pay documents (they never match these questions, but they are in the index).
- **Questions:** 200 dev questions, a fixed sample (ordered by a hash of the question id).
  Each has exactly 2 gold paragraphs; most need both (multi-hop).
- **Method:** for each question, the top 40 dense and the top 40 BM25 chunks are fetched once.
  Every configuration then ranks documents from those same candidates, so the configurations
  differ only in how they rank.
- **Metrics:** Recall@K is the share of the 2 gold documents found in the top K. MRR is the
  mean of 1 / (rank of the first gold document).

## Results

| Configuration | Recall@2 | Recall@5 | Recall@10 | MRR | Ranking ms |
|---|---|---|---|---|---|
| dense | 0.615 | 0.750 | 0.792 | 0.868 | 0 |
| sparse (BM25) | 0.522 | 0.665 | 0.785 | 0.825 | 0 |
| hybrid RRF k=60 (paper) | 0.598 | 0.770 | 0.855 | 0.874 | 0 |
| hybrid RRF k=60, BM25 x0.5 | 0.600 | 0.762 | 0.823 | 0.862 | 0 |
| hybrid RRF k=10 | 0.615 | 0.795 | 0.875 | 0.880 | 0 |
| hybrid RRF k=10, BM25 x0.5 | 0.605 | 0.777 | 0.823 | 0.865 | 0 |
| **hybrid RRF k=10 + MiniLM-L-6 reranker** | **0.665** | **0.818** | **0.892** | **0.932** | 1,128 |
| hybrid RRF k=10 + MiniLM-L-12 reranker | 0.680 | 0.823 | 0.885 | 0.933 | 2,039 |

"Ranking ms" is the time to rank one question's candidates on a laptop CPU, after the
searches (which every configuration shares). Fusion alone takes well under a millisecond;
a reranker reads the top 20 fused chunks with the question, one pair at a time.

## Findings

1. **Hybrid beats either retriever alone.** RRF k=10 finds 87.5% of gold documents in the top
   10, against 79.2% for dense and 78.5% for BM25. The two retrievers miss different
   documents: dense misses exact names and rare terms, BM25 misses paraphrases.
2. **k=10 beats the paper's k=60.** A smaller k gives the top ranks of each list more weight.
   With only 40 candidates per list, k=60 flattens the scores so much that a document ranked
   low by both retrievers can overtake one ranked first by one of them.
3. **Down-weighting BM25 hurts.** Halving its weight lowers Recall@10 by 3 to 5 points at both
   values of k. BM25 alone is weaker, but the documents only it finds matter: in multi-hop
   questions, the second gold paragraph is often found through an exact entity name.
4. **A cross-encoder reranker improves every metric.** On top of RRF k=10, MiniLM-L-6 raises
   MRR from 0.880 to 0.932 and Recall@2 from 0.615 to 0.665: the right paragraph is first
   more often, and both gold paragraphs are in the top 2 more often. The bi-encoder compares
   two separate summaries; the cross-encoder reads question and passage together.
5. **The larger reranker isn't worth its time.** MiniLM-L-12 is within a point of L-6 on
   every metric (better at Recall@2, worse at Recall@10) and takes twice as long.
6. **Recall@2 stays the hardest.** Even reranked it is 0.67: the second hop often names an
   entity that appears only in the first paragraph, so no ranking of the question's own
   candidates can find it. The agent's follow-up searches close that gap.

**Default:** `RRF_K=10` with equal weights (`core/config.py`). The MiniLM-L-6 reranker is
available (`RERANK_MODEL`) but off: in the answer evaluation it didn't make the answers better
([ADR-0011](../decisions/0011-cross-encoder-reranking.md)).

## Limits

- 200 questions: differences of 1–2 points are within noise; the k=10 vs k=60 and hybrid vs
  single-retriever gaps (3–8 points at Recall@5/10) are not.
- Configurations share one candidate pool of 40 per retriever, so recall beyond those
  candidates is not measured; a reranker only reorders the top 20 fused chunks and can't
  find a document fusion ranked below them.
- RRF was tuned on these 200 questions; the rerankers were not tuned (the model and the 20
  candidates were fixed before the run), but they are measured on the same questions.
