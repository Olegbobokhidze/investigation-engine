"""Document CRUD: keeps the Postgres row and the document's chunks in Qdrant in step."""

import asyncio
import uuid

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from investigation_engine.core.errors import DuplicateDocumentError, ForbiddenError, NotFoundError
from investigation_engine.documents.models import Document, DocumentOrigin
from investigation_engine.ingestion.chunking import Chunk, Chunker
from investigation_engine.ingestion.pipeline import (
    PreparedDocument,
    chunk_records,
    embedding_text,
    prepare_document,
)
from investigation_engine.retrieval.embeddings import TextEmbedder
from investigation_engine.retrieval.vector_store import VectorStore

log = structlog.get_logger()


def new_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        embedder: TextEmbedder,
        vector_store: VectorStore,
        chunker: Chunker,
    ) -> None:
        self._session = session
        self._embedder = embedder
        self._vector_store = vector_store
        self._chunker = chunker

    async def list_documents(
        self, search: str, page: int, page_size: int
    ) -> tuple[list[Document], int]:
        """One page of documents, newest first, matching `search` in the title or id."""
        query = select(Document)
        if search:
            pattern = f"%{search}%"
            query = query.where(or_(Document.title.ilike(pattern), Document.id.ilike(pattern)))

        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        rows = await self._session.scalars(
            query.order_by(Document.created_at.desc(), Document.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), total or 0

    async def upload(self, content: bytes, file_name: str) -> Document:
        """Indexes a new file. Raises `DuplicateDocumentError` if its content is indexed."""
        prepared = prepare_document(content, file_name, self._chunker)
        existing_id = await self._find_id_by_hash(prepared.content_hash)
        if existing_id is not None:
            raise DuplicateDocumentError(existing_id)

        document = Document(
            id=new_document_id(),
            title=file_name,
            origin=DocumentOrigin.UPLOAD,
        )
        self._apply(document, prepared)
        self._session.add(document)
        try:
            # Flush first: the unique hash constraint catches a concurrent identical upload
            # before we spend time embedding.
            await self._session.flush()
        except IntegrityError as error:
            await self._session.rollback()
            existing_id = await self._find_id_by_hash(prepared.content_hash)
            raise DuplicateDocumentError(existing_id or "another document") from error

        await self._index_and_commit(document, prepared.chunks)
        log.info("document_uploaded", document_id=document.id, chunk_count=document.chunk_count)
        return document

    async def replace(self, document_id: str, content: bytes, file_name: str) -> Document:
        document = await self._get_editable(document_id)
        prepared = prepare_document(content, file_name, self._chunker)
        existing_id = await self._find_id_by_hash(prepared.content_hash)
        if existing_id is not None and existing_id != document_id:
            raise DuplicateDocumentError(existing_id)

        document.title = file_name
        self._apply(document, prepared)
        # Old chunks go first: the new version may have fewer, and leftovers would be found.
        await self._vector_store.delete_document(document_id)
        await self._index_and_commit(document, prepared.chunks)
        log.info("document_replaced", document_id=document_id, chunk_count=document.chunk_count)
        return document

    async def delete(self, document_id: str) -> None:
        document = await self._get_editable(document_id)
        await self._vector_store.delete_document(document_id)
        await self._session.delete(document)
        await self._session.commit()
        log.info("document_deleted", document_id=document_id)

    async def _get_editable(self, document_id: str) -> Document:
        document = await self._session.get(Document, document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} does not exist.")
        if document.origin == DocumentOrigin.DATASET:
            raise ForbiddenError("Dataset documents are read-only.")
        return document

    async def _find_id_by_hash(self, hash_value: str) -> str | None:
        return await self._session.scalar(
            select(Document.id).where(Document.content_hash == hash_value)
        )

    async def _index_and_commit(self, document: Document, chunks: list[Chunk]) -> None:
        """Embeds and stores the chunks, then commits the row. On any failure the row change
        is rolled back, so a document never exists in Postgres without its chunks — and a
        failed file can't be committed by the next request on the same session."""
        try:
            texts = [embedding_text(document.title, chunk) for chunk in chunks]
            # Embedding is CPU-bound; a worker thread keeps the server responsive meanwhile.
            embeddings = await asyncio.to_thread(self._embedder.embed_passages, texts)
            await self._vector_store.upsert(chunk_records(document, chunks), embeddings)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    @staticmethod
    def _apply(document: Document, prepared: PreparedDocument) -> None:
        document.file_type = prepared.file_type
        document.text = prepared.text
        document.content_hash = prepared.content_hash
        document.chunk_count = len(prepared.chunks)
        document.file_metadata = prepared.metadata
