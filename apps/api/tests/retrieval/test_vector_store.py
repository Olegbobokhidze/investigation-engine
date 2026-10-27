import os
import uuid
from collections.abc import AsyncIterator

import pytest
from qdrant_client import AsyncQdrantClient

from investigation_engine.retrieval.embeddings import Embedding, SparseVector
from investigation_engine.retrieval.vector_store import ChunkRecord, VectorStore

pytestmark = pytest.mark.integration

# Local Qdrant from docker-compose.yml (`make services-up`), never the cloud cluster.
QDRANT_URL = os.environ.get("TEST_QDRANT_URL", "http://localhost:6333")
DENSE_SIZE = 4


@pytest.fixture
async def store() -> AsyncIterator[VectorStore]:
    collection = f"test_{uuid.uuid4().hex}"
    vector_store = VectorStore(QDRANT_URL, api_key=None, collection=collection)
    await vector_store.ensure_collection(DENSE_SIZE)
    yield vector_store
    await vector_store.close()
    client = AsyncQdrantClient(url=QDRANT_URL)
    await client.delete_collection(collection)
    await client.close()


def _record(document_id: str, chunk_index: int) -> ChunkRecord:
    return ChunkRecord(
        document_id=document_id,
        document_title=f"{document_id}.md",
        file_type="md",
        origin="upload",
        chunk_index=chunk_index,
        section=None,
        text=f"Chunk {chunk_index} of {document_id}.",
    )


def _embedding(seed: float) -> Embedding:
    return Embedding(
        dense=[seed, 1.0, 0.5, 0.25],
        sparse=SparseVector(indices=[1, 7], values=[1.0, seed]),
    )


async def test_ensure_collection_is_idempotent(store: VectorStore) -> None:
    await store.ensure_collection(DENSE_SIZE)

    assert await store.count() == 0


async def test_upsert_twice_overwrites_instead_of_duplicating(store: VectorStore) -> None:
    records = [_record("doc_a", 0), _record("doc_a", 1)]

    await store.upsert(records, [_embedding(0.1), _embedding(0.2)])
    await store.upsert(records, [_embedding(0.3), _embedding(0.4)])

    assert await store.count() == 2


async def test_delete_document_removes_only_its_chunks(store: VectorStore) -> None:
    await store.upsert(
        [_record("doc_a", 0), _record("doc_a", 1), _record("doc_b", 0)],
        [_embedding(0.1), _embedding(0.2), _embedding(0.3)],
    )

    await store.delete_document("doc_a")

    assert await store.count() == 1


async def test_document_chunks_returns_one_documents_first_chunks_in_order(
    store: VectorStore,
) -> None:
    await store.upsert(
        [_record("doc_a", 2), _record("doc_a", 0), _record("doc_a", 1), _record("doc_b", 0)],
        [_embedding(0.1), _embedding(0.2), _embedding(0.3), _embedding(0.4)],
    )

    chunks = await store.document_chunks("doc_a", limit=2)

    assert [(chunk.document_id, chunk.chunk_index) for chunk in chunks] == [
        ("doc_a", 0),
        ("doc_a", 1),
    ]
