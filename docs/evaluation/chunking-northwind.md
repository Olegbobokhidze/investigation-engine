# Chunking evaluation: Northwind Pay

`make eval-chunking` · raw numbers in [`chunking-northwind.json`](chunking-northwind.json)

## Setup

- **Why Northwind:** a HotpotQA paragraph is one chunk at any of these sizes, so chunking
  can only be compared on documents with several sections. The 12 Northwind documents are
  indexed together with 1,000 HotpotQA paragraphs as distractors, so search can go wrong.
- **Questions:** the 20 answerable Northwind evaluation questions (simple, multi-hop,
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
| fixed 60 words, overlap 12 | 27 | 0.783 | 0.783 | **0.950** | 0.825 | 277 |
| structured 60 words | 43 | 0.833 | 0.858 | 0.925 | 0.875 | 199 |
| fixed 120 words, overlap 24 | 14 | 0.808 | 0.858 | 0.900 | 0.875 | 483 |
| structured 120 words | 36 | 0.833 | 0.883 | 0.925 | 0.900 | 314 |
| fixed 200 words, overlap 40 | 12 | 0.808 | 0.900 | 0.900 | **0.925** | 558 |
| **structured 200 words** | 35 | **0.858** | **0.908** | 0.925 | 0.900 | 361 |

## Findings

1. **Structure-aware chunking finds the right documents more often at every size**
   (Recall@3 +0.03 to +0.05, Recall@5 +0.01 to +0.08). A chunk that is one section has one
   topic, so its embedding isn't diluted by the next section's content. MRR is mixed: fixed
   60-word chunks rank the first gold document highest (0.950 against 0.925).
2. **It gives the LLM about a third less text.** At 200 words, structured chunks reach fact
   recall 0.90 with 361 words of context; fixed chunks reach 0.93 with 558 (35% more). The
   0.025 difference is half a fact over 20 questions; at 60 and 120 words structured chunks
   also have the higher fact recall.
3. **Very small chunks lose facts.** At 60 words both strategies have their lowest fact
   recall (0.83 and 0.88): a fact and the subject it is about end up in different chunks.

**Default:** `CHUNKING_STRATEGY=structured`, `CHUNK_MAX_WORDS=200` (`core/config.py`): the best
Recall@3 and Recall@5, with fact recall within 0.03 of the best at 35% less context.

## Limits

20 questions over 12 documents: one question moves a metric by about 0.05, so only the
consistent direction across sizes is a finding, not any single gap. The documents are short
(100–250 words); long uploads would make the strategies differ more. The run of 27 October
added the support handbook and its 3 questions; the earlier 17-question run pointed the same
way.
