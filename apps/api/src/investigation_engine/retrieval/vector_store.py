"""Qdrant adapter: stores each chunk as one point with a dense and a sparse vector.

The chunk's text and its document's details travel in the point's payload, so a search
result can be shown and cited without another database round trip.
"""

import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ApiException

from investigation_engine.core.errors import UpstreamError
from investigation_engine.retrieval.embeddings import Embedding

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "bm25"

# Fixed namespace, so a chunk's point id is the same on every run (re-indexing overwrites
# instead of duplicating).
_POINT_ID_NAMESPACE = uuid.UUID("6f1c2b9e-3d4a-4e8b-9c7d-2a5f0e1b8c34")


@dataclass(frozen=True)
class ChunkRecord:
    """A chunk's payload in Qdrant."""

    document_id: str
    document_title: str
    file_type: str
    origin: str
    chunk_index: int
    section: str | None
    text: str


def chunk_point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{document_id}:{chunk_index}"))


@asynccontextmanager
async def _upstream_errors() -> AsyncIterator[None]:
    try:
        yield
    except ApiException as error:
        raise UpstreamError("The vector store is unavailable. Please try again.") from error


class VectorStore:
    def __init__(self, url: str, api_key: str | None, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key)
        self.collection = collection

    async def ensure_collection(self, dense_size: int) -> None:
        """Creates the collection and its payload index if they don't exist yet."""
        async with _upstream_errors():
            if await self._client.collection_exists(self.collection):
                return
            await self._client.create_collection(
                self.collection,
                vectors_config={
                    DENSE_VECTOR: models.VectorParams(
                        size=dense_size, distance=models.Distance.COSINE
                    )
                },
                # IDF modifier: Qdrant computes inverse document frequency over the whole
                # collection, completing BM25 (fastembed supplies the term-frequency part).
                sparse_vectors_config={
                    SPARSE_VECTOR: models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            # Indexed so deleting a document's chunks doesn't scan every point.
            await self._client.create_payload_index(
                self.collection, "document_id", models.PayloadSchemaType.KEYWORD
            )

    async def upsert(self, records: Sequence[ChunkRecord], embeddings: Sequence[Embedding]) -> None:
        points = [
            models.PointStruct(
                id=chunk_point_id(record.document_id, record.chunk_index),
                vector={
                    DENSE_VECTOR: embedding.dense,
                    SPARSE_VECTOR: models.SparseVector(
                        indices=embedding.sparse.indices, values=embedding.sparse.values
                    ),
                },
                payload=asdict(record),
            )
            for record, embedding in zip(records, embeddings, strict=True)
        ]
        async with _upstream_errors():
            await self._client.upsert(self.collection, points, wait=True)

    async def delete_document(self, document_id: str) -> None:
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id", match=models.MatchValue(value=document_id)
                    )
                ]
            )
        )
        async with _upstream_errors():
            await self._client.delete(self.collection, points_selector=selector, wait=True)

    async def count(self) -> int:
        async with _upstream_errors():
            result = await self._client.count(self.collection, exact=True)
        return result.count

    async def close(self) -> None:
        await self._client.close()
