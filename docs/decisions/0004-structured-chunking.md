# ADR-0004: Structure-aware chunking, up to 200 words

**Status:** accepted · 2026-10-27

## Context

Chunks are what gets embedded, retrieved and shown to the LLM. A chunk that mixes two
sections has a blurred embedding; a chunk that cuts a fact from its subject loses the fact.
Larger chunks cost more LLM tokens per passage. The assignment asks for at least two
strategies, compared.

## Decision

`StructuredChunker` in `apps/api/src/investigation_engine/ingestion/chunking.py`: pack whole
paragraphs up to 200 words, start a new chunk at every Markdown heading and keep that
heading as the chunk's section; split only a paragraph longer than the limit, at sentence
boundaries. `FixedSizeChunker` (windows with 20% overlap) stays as the alternative,
selected by `CHUNKING_STRATEGY`.

## Alternatives considered

- **Fixed-size windows with overlap** at 60, 120 and 200 words: measured below.
- **Semantic chunking** (split where embeddings of neighbouring sentences diverge): one
  embedding per sentence at index time, 66k documents on a laptop CPU.

## Evidence

[`docs/evaluation/chunking-northwind.md`](../evaluation/chunking-northwind.md), 20 Northwind
questions with 1,000 HotpotQA distractors: structured chunks have the higher Recall@3 and
Recall@5 at every size. At 200 words: Recall@3 0.858 against 0.808, fact recall 0.900
against 0.925, with 361 words of context against 558. Tests:
`apps/api/tests/ingestion/test_chunking.py`.

## Consequences

Documents without headings (TXT, most PDFs) fall back to paragraph packing. pypdf loses
paragraph breaks inside a page, so a PDF page is packed by sentences.
