import uuid
from collections.abc import AsyncIterator
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


@pytest.fixture
async def retriever() -> AsyncIterator[Retriever]:
    collection = f"test_{uuid.uuid4().hex}"
    embedder = FakeEmbedder()
    store = VectorStore(TEST_QDRANT_URL, api_key=None, collection=collection)
    await store.ensure_collection(embedder.dense_size)
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
    await store.upsert(records, embedder.embed_passages(list(TEXTS.values())))
    yield Retriever(
        embedder,
        store,
        FusionSettings(candidates=10, rrf_k=60, dense_weight=1.0, sparse_weight=1.0),
    )
    await store.close()
    client = AsyncQdrantClient(url=TEST_QDRANT_URL)
    await client.delete_collection(collection)
    await client.close()


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
