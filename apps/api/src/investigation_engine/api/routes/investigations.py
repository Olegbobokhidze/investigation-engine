import asyncio
import time
from collections.abc import AsyncIterator, Callable

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from investigation_engine.api.dependencies import (
    AnswerCacheDependency,
    InvestigatorDependency,
    MetricsDependency,
    take_investigation_quota,
)
from investigation_engine.api.schemas.base import ApiModel, ErrorDetail
from investigation_engine.api.schemas.investigations import (
    CreateInvestigationRequest,
    InvestigationResponse,
    InvestigationStepResponse,
)
from investigation_engine.core.errors import AppError
from investigation_engine.core.monitoring import Metrics
from investigation_engine.investigation.agent import Investigator
from investigation_engine.investigation.cache import AnswerCache
from investigation_engine.investigation.models import Investigation, Step

router = APIRouter(prefix="/investigations", tags=["investigations"])

log = structlog.get_logger()


@router.post("")
async def create_investigation(
    body: CreateInvestigationRequest,
    request: Request,
    investigator: InvestigatorDependency,
    cache: AnswerCacheDependency,
    metrics: MetricsDependency,
) -> InvestigationResponse:
    """Answers a question from the documents, with citations, or abstains."""
    investigation = cache.get(body.question)
    if investigation is not None:
        metrics.record_cache_hit()
    else:
        # After the investigator dependency, so a request the app can't serve (no LLM key)
        # isn't counted, and after the cache, so a repeated question is free.
        take_investigation_quota(request)
        investigation = await _investigate(investigator, cache, metrics, body.question)
    return InvestigationResponse.model_validate(investigation)


@router.post("/stream")
async def stream_investigation(
    body: CreateInvestigationRequest,
    request: Request,
    investigator: InvestigatorDependency,
    cache: AnswerCacheDependency,
    metrics: MetricsDependency,
) -> StreamingResponse:
    """The same investigation as Server-Sent Events: a `step` event as each step is taken,
    then one `result` event (the body `POST /investigations` returns) or one `error` event
    (the usual error envelope). A cached answer sends its steps and result at once."""
    cached = cache.get(body.question)
    if cached is not None:
        metrics.record_cache_hit()
        events = _cached_events(cached)
    else:
        take_investigation_quota(request)
        events = _events(investigator, cache, metrics, body.question)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        # Proxies must pass each event on at once instead of buffering the response.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _investigate(
    investigator: Investigator,
    cache: AnswerCache,
    metrics: Metrics,
    question: str,
    on_step: Callable[[Step], None] | None = None,
) -> Investigation:
    """Runs the agent, records it in the metrics and keeps the answer for repeat questions."""
    started = time.monotonic()
    try:
        investigation = await investigator.investigate(question, on_step=on_step)
    except AppError:
        metrics.record_failed_investigation()
        raise
    metrics.record_investigation(
        investigation.status,
        investigation.usage.llm_calls,
        investigation.usage.total_tokens,
        time.monotonic() - started,
    )
    cache.put(question, investigation)
    return investigation


class _ErrorEvent(ApiModel):
    error: ErrorDetail


async def _events(
    investigator: Investigator, cache: AnswerCache, metrics: Metrics, question: str
) -> AsyncIterator[str]:
    # The agent runs as a task and puts its steps on a queue; None marks the end.
    steps: asyncio.Queue[Step | None] = asyncio.Queue()
    task = asyncio.create_task(
        _investigate(investigator, cache, metrics, question, on_step=steps.put_nowait)
    )
    task.add_done_callback(lambda _: steps.put_nowait(None))
    try:
        while (step := await steps.get()) is not None:
            yield _event("step", InvestigationStepResponse.model_validate(step))
        try:
            investigation = task.result()
        except AppError as error:
            # The status code is already sent (200), so the error travels as an event.
            log.warning("investigation_stream_failed", code=error.code)
            yield _event(
                "error", _ErrorEvent(error=ErrorDetail(code=error.code, message=error.message))
            )
            return
        yield _event("result", InvestigationResponse.model_validate(investigation))
    finally:
        # A client that disconnects stops the investigation and its LLM spend.
        task.cancel()


async def _cached_events(investigation: Investigation) -> AsyncIterator[str]:
    for step in investigation.steps:
        yield _event("step", InvestigationStepResponse.model_validate(step))
    yield _event("result", InvestigationResponse.model_validate(investigation))


def _event(name: str, data: ApiModel) -> str:
    """One Server-Sent Event; the JSON has no newlines, so it fits on one `data:` line."""
    return f"event: {name}\ndata: {data.model_dump_json(by_alias=True)}\n\n"
