# Chunking evaluation: Northwind Pay

`make eval-chunking` · raw numbers in [`chunking-northwind.json`](chunking-northwind.json)

## Setup

- **Why Northwind:** a HotpotQA paragraph is one chunk at any of these sizes, so chunking
  can only be compared on documents with several sections. The 11 Northwind documents are
  indexed together with 1,000 HotpotQA paragraphs as distractors, so search can go wrong.
- **Questions:** the 17 answerable Northwind evaluation questions (simple, multi-hop,
  contradictory), each with gold documents and the exact facts an answer needs
  (`key_facts` in `apps/api/data/eval/northwind-questions.jsonl`; the runner checks every
  fact is in the corpus).
- **Configurations:** fixed-size chunks (20% overlap) and structure-aware chunks (split at
  headings and paragraphs, no overlap) at 60, 120 and 200 words. Every configuration gets
  its own temporary collection on a local Qdrant and is searched with the production hybrid
  search (RRF k=10).
- **Metrics:** document Recall@3/5 and MRR (are the right documents found); fact recall@5
  (are the needed facts inside the 5 chunks the LLM reads); context words@5 (what those
  chunks cost).

## Results

| Configuration | Northwind chunks | Recall@3 | Recall@5 | MRR | Fact recall@5 | Context words@5 |
|---|---|---|---|---|---|---|
| fixed 60 words, overlap 12 | 25 | 0.775 | 0.775 | 0.941 | 0.824 | 278 |
| structured 60 words | 41 | 0.833 | 0.833 | 0.941 | 0.853 | 195 |
| fixed 120 words, overlap 24 | 13 | 0.804 | 0.863 | 0.912 | 0.882 | 481 |
| structured 120 words | 35 | 0.833 | 0.863 | 0.941 | 0.882 | 305 |
| fixed 200 words, overlap 40 | 11 | 0.804 | 0.882 | 0.912 | 0.912 | 556 |
| **structured 200 words** | 34 | **0.863** | **0.892** | **0.941** | 0.882 | 354 |

## Findings

1. **Structure-aware chunking finds the right documents more often at every size**
   (Recall@3 +0.03 to +0.06, MRR equal or higher). A chunk that is one section has one
   topic, so its embedding isn't diluted by the next section's content.
2. **It gives the LLM 35–40% less text for the same facts.** At 200 words, structured
   chunks reach fact recall 0.88 with 354 words of context; fixed chunks reach 0.91 with
   556. The 0.03 difference is one fact in 17 questions.
3. **Very small chunks lose facts.** At 60 words both strategies drop below 0.86 fact
   recall: a fact and the subject it is about end up in different chunks.

**Default:** `CHUNKING_STRATEGY=structured`, `CHUNK_MAX_WORDS=200` (`core/config.py`).

## Limits

17 questions over 11 documents: one question moves a metric by about 0.06, so only the
consistent direction across sizes is a finding, not any single gap. The documents are short
(100–250 words); long uploads would make the strategies differ more.
