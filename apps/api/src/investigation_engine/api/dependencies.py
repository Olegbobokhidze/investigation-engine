"""FastAPI dependencies shared by routes.

Long-lived objects (database pool, embedding models, Qdrant client) are created once in
`main.lifespan` and kept on `app.state`; these functions hand them to routes.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from investigation_engine.core.config import Settings
from investigation_engine.core.database import Database
from investigation_engine.documents.service import DocumentService
from investigation_engine.ingestion.chunking import create_chunker
from investigation_engine.retrieval.embeddings import TextEmbedder
from investigation_engine.retrieval.vector_store import VectorStore


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One database session per request, closed when the response is sent."""
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_document_service(request: Request, session: SessionDependency) -> DocumentService:
    settings: Settings = request.app.state.settings
    embedder: TextEmbedder = request.app.state.embedder
    vector_store: VectorStore = request.app.state.vector_store
    chunker = create_chunker(
        settings.chunking_strategy, settings.chunk_max_words, settings.chunk_overlap_words
    )
    return DocumentService(session, embedder, vector_store, chunker)


DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]
