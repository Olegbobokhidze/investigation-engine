"""Dense (semantic) and sparse (BM25 keyword) embeddings, computed locally with fastembed.

Dense vectors capture meaning ("payment delays" ≈ "checkout latency"); sparse BM25 vectors
capture exact terms ("CHG-2291"). Hybrid search queries both and fuses the results.

Models run on CPU (ONNX) and are synchronous: call them from async code through
`asyncio.to_thread`, so a long embedding job doesn't block the event loop.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from fastembed import SparseTextEmbedding, TextEmbedding

# BM25 term weights; Qdrant applies the IDF part at query time (see vector_store.py).
SPARSE_MODEL = "Qdrant/bm25"

# Texts in a batch are padded to the longest one, so small batches waste less compute on
# padding: 32 embedded real HotpotQA paragraphs 1.5x faster than fastembed's default 256.
_DENSE_BATCH_SIZE = 32


@dataclass(frozen=True)
class SparseVector:
    indices: list[int]
    values: list[float]


@dataclass(frozen=True)
class Embedding:
    dense: list[float]
    sparse: SparseVector


class TextEmbedder(Protocol):
    """What the app needs from an embedder; tests substitute a fast fake."""

    dense_size: int

    def embed_passages(self, texts: Sequence[str]) -> list[Embedding]: ...

    def embed_query(self, query: str) -> Embedding: ...


class Embedder:
    def __init__(self, dense_model: str, query_prefix: str) -> None:
        # Downloads the models on first use and caches them on disk.
        self._dense = TextEmbedding(dense_model)
        self._sparse = SparseTextEmbedding(SPARSE_MODEL)
        self._query_prefix = query_prefix
        self.dense_size: int = self._dense.embedding_size

    def embed_passages(self, texts: Sequence[str]) -> list[Embedding]:
        dense = self._dense.passage_embed(texts, batch_size=_DENSE_BATCH_SIZE)
        sparse = self._sparse.passage_embed(texts)
        return [
            Embedding(
                dense=dense_vector.tolist(),
                sparse=SparseVector(
                    indices=sparse_vector.indices.tolist(),
                    values=sparse_vector.values.tolist(),
                ),
            )
            for dense_vector, sparse_vector in zip(dense, sparse, strict=True)
        ]

    def embed_query(self, query: str) -> Embedding:
        dense_vector = next(iter(self._dense.query_embed(self._query_prefix + query)))
        # BM25 queries are plain terms: the instruction prefix would only add noise words.
        sparse_vector = next(iter(self._sparse.query_embed(query)))
        return Embedding(
            dense=dense_vector.tolist(),
            sparse=SparseVector(
                indices=sparse_vector.indices.tolist(),
                values=sparse_vector.values.tolist(),
            ),
        )
