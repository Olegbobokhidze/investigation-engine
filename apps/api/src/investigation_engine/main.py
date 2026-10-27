"""FastAPI application factory.

Run with `uvicorn --factory investigation_engine.main:create_app`, so settings are read
when the server starts rather than as a side effect of importing this module.
"""

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

# Importing the models registers their tables with Base.metadata before create_tables runs.
import investigation_engine.documents.models  # noqa: F401
from investigation_engine.api.routes import documents, health, investigations, metrics
from investigation_engine.core.config import Settings, get_settings
from investigation_engine.core.database import Database
from investigation_engine.core.errors import AppError
from investigation_engine.core.logging import configure_logging
from investigation_engine.core.monitoring import Metrics
from investigation_engine.core.rate_limit import DailyQuota
from investigation_engine.investigation.cache import InMemoryAnswerCache
from investigation_engine.llm.client import ChatModel, LlmClient
from investigation_engine.retrieval.embeddings import Embedder, TextEmbedder
from investigation_engine.retrieval.reranking import CrossEncoderReranker
from investigation_engine.retrieval.search import FusionSettings, Retriever
from investigation_engine.retrieval.vector_store import VectorStore


def create_app(
    settings: Settings | None = None,
    *,
    embedder: TextEmbedder | None = None,
    llm: ChatModel | None = None,
) -> FastAPI:
    """Builds the app. Tests pass `embedder` and `llm` to skip the real models."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.env == "prod")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Runs once at startup (before `yield`) and once at shutdown (after it).
        database = Database(settings.database_url.get_secret_value())
        await database.create_tables()
        text_embedder = embedder or Embedder(
            settings.embedding_model, settings.embedding_query_prefix
        )
        vector_store = VectorStore.from_settings(settings)
        await vector_store.ensure_collection(text_embedder.dense_size)
        # Without an API key the app still serves documents; investigations answer 503.
        llm_client = None if llm or not settings.llm_api_key else LlmClient.from_settings(settings)

        app.state.settings = settings
        app.state.database = database
        app.state.embedder = text_embedder
        app.state.vector_store = vector_store
        reranker = CrossEncoderReranker(settings.rerank_model) if settings.rerank_model else None
        app.state.retriever = Retriever(
            text_embedder, vector_store, FusionSettings.from_settings(settings), reranker
        )
        app.state.llm = llm or llm_client
        app.state.investigation_quota = DailyQuota(
            per_client=settings.investigations_per_client_per_day,
            total=settings.investigations_per_day,
        )
        app.state.answer_cache = InMemoryAnswerCache(
            settings.answer_cache_size, settings.answer_cache_ttl_s
        )
        yield
        if llm_client:
            await llm_client.close()
        await vector_store.close()
        await database.dispose()

    app = FastAPI(title="Investigation Engine", version="0.1.0", lifespan=lifespan)
    live_metrics = Metrics()
    app.state.metrics = live_metrics

    @app.middleware("http")
    async def record_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        status_code = 500  # unless a response comes back: an unhandled error is a 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # The route template (/documents/{document_id}), so ids don't make a series each;
            # requests that matched no route share one.
            route = request.scope.get("route")
            live_metrics.record_request(
                request.method,
                route.path if isinstance(route, APIRoute) else "unmatched",
                status_code,
                (time.perf_counter() - started) * 1000,
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(investigations.router)
    app.include_router(metrics.router)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    # FastAPI's own validation errors (bad query params, missing fields) use the same
    # envelope as ours, so clients handle a single error shape.
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        field = ".".join(str(part) for part in first["loc"][1:]) or "request"
        return _error_response(422, "invalid_input", f"Invalid {field}: {first['msg']}.")

    return app


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )
