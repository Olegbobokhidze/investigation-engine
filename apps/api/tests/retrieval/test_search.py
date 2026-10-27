import uuid
from collections.abc import AsyncIterator, Sequence
from itertools import pairwise

import pytest
from qdrant_client import AsyncQdrantClient

from investigation_engine.retrieval.search import FusionSettings, Retriever
from investigation_engine.retrieval.vector_store import ChunkRecord, VectorStore
from tests.conftest import TEST_QDRANT_URL, FakeEmbedder

pytestmark = pytest.mark.integration

TEXTS = {
    "doc_change": "CHG-2291 reduced the payments-db pool to 20 connections.",
    "doc_incident": "Checkout latency rose and payments slowed down in March.",
    "doc_film": "Ed Wood is a 1994 film directed by Tim Burton.",
}


FUSION = FusionSettings(candidates=10, rrf_k=60, dense_weight=1.0, sparse_weight=1.0)


@pytest.fixture
async def store() -> AsyncIterator[VectorStore]:
    """A fresh collection holding the three test documents, embedded by the fake."""
    collection = f"test_{uuid.uuid4().hex}"
    embedder = FakeEmbedder()
    vector_store = VectorStore(TEST_QDRANT_URL, api_key=None, collection=collection)
    await vector_store.ensure_collection(embedder.dense_size)
    records = [
        ChunkRecord(
            document_id=document_id,
            document_title=document_id,
            file_type="txt",
            origin="upload",
            chunk_index=0,
            section=None,
            text=text,
        )
        for document_id, text in TEXTS.items()
    ]
    await vector_store.upsert(records, embedder.embed_passages(list(TEXTS.values())))
    yield vector_store
    await vector_store.close()
    client = AsyncQdrantClient(url=TEST_QDRANT_URL)
    await client.delete_collection(collection)
    await client.close()


@pytest.fixture
def retriever(store: VectorStore) -> Retriever:
    return Retriever(FakeEmbedder(), store, FUSION)


async def test_sparse_search_finds_the_exact_term(retriever: Retriever) -> None:
    hits = await retriever.search("chg-2291", limit=1, mode="sparse")

    assert [hit.record.document_id for hit in hits] == ["doc_change"]


async def test_hybrid_search_returns_fused_unique_chunks(retriever: Retriever) -> None:
    hits = await retriever.search("payments pool chg-2291", limit=3, mode="hybrid")

    document_ids = [hit.record.document_id for hit in hits]
    # The fake's dense vectors carry no meaning, so only BM25's exact match is predictable.
    assert "doc_change" in document_ids
    assert len(document_ids) == len(set(document_ids))
    assert all(earlier.score >= later.score for earlier, later in pairwise(hits))


async def test_search_respects_the_limit(retriever: Retriever) -> None:
    for mode in ("dense", "sparse", "hybrid"):
        assert len(await retriever.search("payments", limit=2, mode=mode)) <= 2


class ReverseReranker:
    """Prefers the candidate fusion ranked last, so a reorder is visible."""

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        return [float(index) for index in range(len(texts))]


async def test_hybrid_search_with_a_reranker_returns_its_order(
    retriever: Retriever, store: VectorStore
) -> None:
    fused = await retriever.search("payments pool chg-2291", limit=3)
    reranking = Retriever(FakeEmbedder(), store, FUSION, ReverseReranker())

    reranked = await reranking.search("payments pool chg-2291", limit=3)

    assert [hit.record.document_id for hit in reranked] == [
        hit.record.document_id for hit in reversed(fused)
    ]
