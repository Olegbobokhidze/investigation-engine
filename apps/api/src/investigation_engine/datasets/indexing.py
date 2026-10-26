"""Bulk indexing shared by the dataset loaders (HotpotQA, the synthetic corpus).

Uploads index one document per request (documents/service.py); a dataset is thousands, so
here documents are embedded and stored in batches, and a rerun resumes where it stopped.
"""

import asyncio
import time
from dataclasses import dataclass

import structlog
from sqlalchemy import select

import investigation_engine.documents.models  # noqa: F401  (registers the table)
from investigation_engine.core.config import Settings
from investigation_engine.core.database import Database
from investigation_engine.documents.models import Document
from investigation_engine.ingestion.chunking import Chunk
from investigation_engine.ingestion.pipeline import chunk_records, embedding_text
from investigation_engine.retrieval.embeddings import Embedder
from investigation_engine.retrieval.vector_store import ChunkRecord, VectorStore

log = structlog.get_logger()

# Documents per round of embed → Qdrant → Postgres; also the unit of resumability.
BATCH_SIZE = 256


@dataclass(frozen=True)
class DatasetDocument:
    document: Document
    chunks: list[Chunk]


async def index_dataset(settings: Settings, items: list[DatasetDocument]) -> None:
    """Indexes the documents that aren't stored yet, in batches."""
    database = Database(settings.database_url.get_secret_value())
    await database.create_tables()
    embedder = Embedder(settings.embedding_model, settings.embedding_query_prefix)
    vector_store = VectorStore.from_settings(settings)
    await vector_store.ensure_collection(embedder.dense_size)

    async with database.sessions() as session:
        stored_ids = set(await session.scalars(select(Document.id)))
        seen_hashes = set(await session.scalars(select(Document.content_hash)))

    # Skip what's stored (resume) and items whose text repeats under another id.
    pending: list[DatasetDocument] = []
    for item in items:
        if item.document.id in stored_ids or item.document.content_hash in seen_hashes:
            continue
        seen_hashes.add(item.document.content_hash)
        pending.append(item)
    # Similar lengths in a batch means little padding: about 2x faster embedding.
    pending.sort(key=lambda item: len(item.document.text))
    log.info("dataset_indexing", total=len(items), pending=len(pending))

    started = time.perf_counter()
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        records: list[ChunkRecord] = []
        texts: list[str] = []
        for item in batch:
            records.extend(chunk_records(item.document, item.chunks))
            texts.extend(embedding_text(item.document.title, chunk) for chunk in item.chunks)

        embeddings = await asyncio.to_thread(embedder.embed_passages, texts)
        # Qdrant first, Postgres second: a row exists only once its chunks do, so a crash
        # mid-batch is repaired by simply running the loader again.
        await vector_store.upsert(records, embeddings)
        async with database.sessions() as session:
            session.add_all([item.document for item in batch])
            await session.commit()

        done = start + len(batch)
        rate = done / (time.perf_counter() - started)
        log.info("dataset_batch_indexed", done=done, pending=len(pending), per_second=round(rate))

    log.info("dataset_indexed", documents=len(pending), points=await vector_store.count())
    await vector_store.close()
    await database.dispose()
