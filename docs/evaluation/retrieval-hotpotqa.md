# Retrieval evaluation: HotpotQA

`make eval-retrieval` · raw numbers in [`retrieval-hotpotqa.json`](retrieval-hotpotqa.json)

## Setup

- **Corpus:** all 66,581 distinct paragraphs of the HotpotQA dev distractor set, plus the 11
  Northwind Pay documents (they never match these questions, but they are in the index).
- **Questions:** 200 dev questions, a fixed sample (ordered by a hash of the question id).
  Each has exactly 2 gold paragraphs; most need both (multi-hop).
- **Method:** for each question, the top 40 dense and the top 40 BM25 chunks are fetched once.
  Every configuration then ranks documents from those same candidates, so the configurations
  differ only in how they rank.
- **Metrics:** Recall@K is the share of the 2 gold documents found in the top K. MRR is the
  mean of 1 / (rank of the first gold document).

## Results

| Configuration | Recall@2 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| dense | 0.615 | 0.750 | 0.792 | 0.868 |
| sparse (BM25) | 0.522 | 0.665 | 0.785 | 0.825 |
| hybrid RRF k=60 (paper) | 0.598 | 0.770 | 0.855 | 0.874 |
| hybrid RRF k=60, BM25 x0.5 | 0.600 | 0.760 | 0.823 | 0.862 |
| **hybrid RRF k=10** | **0.615** | **0.795** | **0.875** | **0.880** |
| hybrid RRF k=10, BM25 x0.5 | 0.605 | 0.777 | 0.823 | 0.865 |

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
4. **Recall@2 barely moves (0.60–0.62).** Getting *both* gold paragraphs into the top 2 is hard
   from the question alone, because the second hop often names an entity that appears only
   in the first paragraph. Retrieving more candidates (top 10) and letting the agent search
   again with what it learned is what closes that gap.

**Default:** `RRF_K=10` with equal weights (`core/config.py`).

## Limits

- 200 questions: differences of 1–2 points are within noise; the k=10 vs k=60 and hybrid vs
  single-retriever gaps (3–8 points at Recall@5/10) are not.
- Configurations share one candidate pool of 40 per retriever, so recall beyond those
  candidates is not measured.
