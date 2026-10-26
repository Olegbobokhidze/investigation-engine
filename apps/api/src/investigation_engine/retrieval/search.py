"""Hybrid search: dense and BM25 candidates from Qdrant, fused with our weighted RRF."""

import asyncio
from dataclasses import dataclass
from typing import Literal

from investigation_engine.retrieval.embeddings import TextEmbedder
from investigation_engine.retrieval.fusion import weighted_rrf
from investigation_engine.retrieval.vector_store import ChunkRecord, ScoredChunk, VectorStore

# "dense" and "sparse" run one retriever alone; the evaluation compares all three.
type SearchMode = Literal["dense", "sparse", "hybrid"]


@dataclass(frozen=True)
class SearchHit:
    record: ChunkRecord
    # RRF score in hybrid mode, the retriever's own similarity otherwise.
    score: float


@dataclass(frozen=True)
class FusionSettings:
    # Candidates fetched from each retriever before fusing; more finds more, costs latency.
    candidates: int
    rrf_k: int
    dense_weight: float
    sparse_weight: float


class Retriever:
    def __init__(
        self, embedder: TextEmbedder, vector_store: VectorStore, fusion: FusionSettings
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._fusion = fusion

    async def search(self, query: str, limit: int, mode: SearchMode = "hybrid") -> list[SearchHit]:
        embedding = await asyncio.to_thread(self._embedder.embed_query, query)
        if mode == "dense":
            dense = await self._vector_store.search_dense(embedding.dense, limit)
            return [SearchHit(record=hit.record, score=hit.score) for hit in dense]
        if mode == "sparse":
            sparse = await self._vector_store.search_sparse(embedding.sparse, limit)
            return [SearchHit(record=hit.record, score=hit.score) for hit in sparse]

        # Both lists come from the same Qdrant cluster, so they can be fetched at once.
        dense, sparse = await asyncio.gather(
            self._vector_store.search_dense(embedding.dense, self._fusion.candidates),
            self._vector_store.search_sparse(embedding.sparse, self._fusion.candidates),
        )
        return self._fuse(dense, sparse)[:limit]

    def _fuse(self, dense: list[ScoredChunk], sparse: list[ScoredChunk]) -> list[SearchHit]:
        records = {hit.point_id: hit.record for hit in [*dense, *sparse]}
        fused = weighted_rrf(
            [[hit.point_id for hit in dense], [hit.point_id for hit in sparse]],
            weights=[self._fusion.dense_weight, self._fusion.sparse_weight],
            k=self._fusion.rrf_k,
        )
        return [SearchHit(record=records[point_id], score=score) for point_id, score in fused]
