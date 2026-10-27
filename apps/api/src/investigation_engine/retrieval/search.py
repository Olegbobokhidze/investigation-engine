"""Hybrid search: dense and BM25 candidates from Qdrant, fused with our weighted RRF, and
optionally re-ranked by a cross-encoder."""

import asyncio
from dataclasses import dataclass
from typing import Literal

from investigation_engine.core.config import Settings
from investigation_engine.retrieval.embeddings import TextEmbedder
from investigation_engine.retrieval.fusion import weighted_rrf
from investigation_engine.retrieval.reranking import Reranker, rerank
from investigation_engine.retrieval.vector_store import ChunkRecord, ScoredChunk, VectorStore

# "dense" and "sparse" run one retriever alone; the evaluation compares all three.
type SearchMode = Literal["dense", "sparse", "hybrid"]


@dataclass(frozen=True)
class SearchHit:
    record: ChunkRecord
    # Reranker score when re-ranked, RRF score in hybrid mode, else the retriever's similarity.
    score: float


@dataclass(frozen=True)
class FusionSettings:
    # Candidates fetched from each retriever before fusing; more finds more, costs latency.
    candidates: int
    rrf_k: int
    dense_weight: float
    sparse_weight: float
    # How many fused candidates the reranker reads (when there is one): it is the slow step.
    rerank_candidates: int = 20

    @classmethod
    def from_settings(cls, settings: Settings) -> "FusionSettings":
        return cls(
            candidates=settings.search_candidates,
            rrf_k=settings.rrf_k,
            dense_weight=settings.rrf_dense_weight,
            sparse_weight=settings.rrf_sparse_weight,
            rerank_candidates=settings.rerank_candidates,
        )


class Retriever:
    def __init__(
        self,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        fusion: FusionSettings,
        reranker: Reranker | None = None,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._fusion = fusion
        self._reranker = reranker

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
        fused = self._fuse(dense, sparse)
        if self._reranker is None:
            return fused[:limit]
        candidates = [hit.record for hit in fused[: self._fusion.rerank_candidates]]
        reranked = await asyncio.to_thread(rerank, query, candidates, self._reranker)
        return [SearchHit(record=record, score=score) for record, score in reranked[:limit]]

    async def read_document(self, document_id: str, limit: int) -> list[ChunkRecord]:
        """A document's first `limit` chunks in order, for reading a passage in context."""
        return await self._vector_store.document_chunks(document_id, limit)

    def _fuse(self, dense: list[ScoredChunk], sparse: list[ScoredChunk]) -> list[SearchHit]:
        records = {hit.point_id: hit.record for hit in [*dense, *sparse]}
        fused = weighted_rrf(
            [[hit.point_id for hit in dense], [hit.point_id for hit in sparse]],
            weights=[self._fusion.dense_weight, self._fusion.sparse_weight],
            k=self._fusion.rrf_k,
        )
        return [SearchHit(record=records[point_id], score=score) for point_id, score in fused]
