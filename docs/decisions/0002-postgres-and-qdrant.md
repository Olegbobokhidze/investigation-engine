# ADR-0002: Postgres is the source of truth, Qdrant is the search index

**Status:** accepted · 2026-10-26

## Context

Documents need a list with search and pagination, deduplication by content, read-only
dataset documents and safe replace and delete. Search needs dense vectors and BM25 over
66k documents, on free tiers.

## Decision

- **Postgres (Neon)** holds one row per document: title, type, origin, metadata, text and a
  unique content hash (`apps/api/src/investigation_engine/documents/models.py`).
- **Qdrant (Qdrant Cloud)** holds one point per chunk with two named vectors, `dense`
  (bge-small, 384 dimensions) and `bm25` (sparse, with Qdrant's IDF), so both searches run in
  one store (`apps/api/src/investigation_engine/retrieval/vector_store.py`).
- **Write order:** chunks go to Qdrant first and the Postgres row is committed last, so a
  document is never listed without its chunks; a failure rolls the row back
  (`apps/api/src/investigation_engine/documents/service.py`).

## Alternatives considered

- **pgvector only:** one database, but Postgres full-text ranking (`ts_rank`) isn't BM25;
  real BM25 needs another extension, and dense plus sparse fusion would be hand-written SQL.
- **Qdrant only:** no unique constraint for deduplication and no substring search on titles;
  the document text would live only in point payloads.

## Evidence

- `apps/api/tests/api/test_documents.py`: duplicate content → 409, dataset documents are
  read-only (403), replace and delete swap or remove the chunks with the row.
- `apps/api/tests/retrieval/test_vector_store.py`: upserts are idempotent and a delete
  removes only that document's chunks.

## Consequences

Two stores can drift if a process dies between the writes; the order above makes the only
possible leftover an orphaned Qdrant point, which a re-index overwrites.
