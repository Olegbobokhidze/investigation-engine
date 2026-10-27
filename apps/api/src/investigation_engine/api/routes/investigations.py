import asyncio
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from investigation_engine.api.dependencies import (
    InvestigationQuotaDependency,
    InvestigatorDependency,
)
from investigation_engine.api.schemas.base import ApiModel, ErrorDetail
from investigation_engine.api.schemas.investigations import (
    CreateInvestigationRequest,
    InvestigationResponse,
    InvestigationStepResponse,
)
from investigation_engine.core.errors import AppError
from investigation_engine.investigation.agent import Investigator
from investigation_engine.investigation.models import Step

router = APIRouter(prefix="/investigations", tags=["investigations"])

log = structlog.get_logger()


@router.post("")
async def create_investigation(
    body: CreateInvestigationRequest,
    investigator: InvestigatorDependency,
    # After the investigator, so a request the app can't serve (no LLM key) isn't counted.
    _quota: InvestigationQuotaDependency,
) -> InvestigationResponse:
    """Answers a question from the documents, with citations, or abstains."""
    investigation = await investigator.investigate(body.question)
    return InvestigationResponse.model_validate(investigation)


@router.post("/stream")
async def stream_investigation(
    body: CreateInvestigationRequest,
    investigator: InvestigatorDependency,
    _quota: InvestigationQuotaDependency,
) -> StreamingResponse:
    """The same investigation as Server-Sent Events: a `step` event as each step is taken,
    then one `result` event (the body `POST /investigations` returns) or one `error` event
    (the usual error envelope)."""
    return StreamingResponse(
        _events(investigator, body.question),
        media_type="text/event-stream",
        # Proxies must pass each event on at once instead of buffering the response.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class _ErrorEvent(ApiModel):
    error: ErrorDetail


async def _events(investigator: Investigator, question: str) -> AsyncIterator[str]:
    # The agent runs as a task and puts its steps on a queue; None marks the end.
    steps: asyncio.Queue[Step | None] = asyncio.Queue()
    task = asyncio.create_task(investigator.investigate(question, on_step=steps.put_nowait))
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


def _event(name: str, data: ApiModel) -> str:
    """One Server-Sent Event; the JSON has no newlines, so it fits on one `data:` line."""
    return f"event: {name}\ndata: {data.model_dump_json(by_alias=True)}\n\n"
