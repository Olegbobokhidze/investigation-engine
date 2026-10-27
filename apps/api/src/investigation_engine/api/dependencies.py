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
from investigation_engine.core.errors import NotConfiguredError
from investigation_engine.core.rate_limit import DailyQuota
from investigation_engine.documents.service import DocumentService
from investigation_engine.ingestion.chunking import chunker_from_settings
from investigation_engine.investigation.agent import Investigator
from investigation_engine.llm.client import ChatModel
from investigation_engine.retrieval.embeddings import TextEmbedder
from investigation_engine.retrieval.search import Retriever
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
    return DocumentService(session, embedder, vector_store, chunker_from_settings(settings))


DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


def get_investigator(request: Request) -> Investigator:
    settings: Settings = request.app.state.settings
    llm: ChatModel | None = request.app.state.llm
    if llm is None:
        raise NotConfiguredError("Investigations need an LLM API key (LLM_API_KEY).")
    retriever: Retriever = request.app.state.retriever
    return Investigator(
        llm,
        retriever,
        max_turns=settings.agent_max_turns,
        search_limit=settings.agent_search_limit,
        cross_check=settings.agent_cross_check,
    )


InvestigatorDependency = Annotated[Investigator, Depends(get_investigator)]


def take_investigation_quota(request: Request) -> None:
    """Counts the investigation against the caller's daily cap, or answers 429."""
    quota: DailyQuota = request.app.state.investigation_quota
    # Behind Caddy this is the visitor's address: uvicorn reads it from X-Forwarded-For.
    quota.take(request.client.host if request.client else "unknown")


InvestigationQuotaDependency = Annotated[None, Depends(take_investigation_quota)]
