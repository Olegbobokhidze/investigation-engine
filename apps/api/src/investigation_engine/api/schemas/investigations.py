"""Request and response bodies for /investigations. Mirrors
apps/web/src/features/investigations/types.ts."""

from typing import Annotated

from pydantic import StringConstraints

from investigation_engine.api.schemas.base import ApiModel
from investigation_engine.documents.models import FileType
from investigation_engine.investigation.models import InvestigationStatus


class CreateInvestigationRequest(ApiModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class SourceResponse(ApiModel):
    number: int
    document_id: str
    document_title: str
    file_type: FileType
    excerpt: str


class ConflictResponse(ApiModel):
    summary: str


class InvestigationStepResponse(ApiModel):
    title: str
    detail: str
    result: str | None


class InvestigationResponse(ApiModel):
    id: str
    question: str
    status: InvestigationStatus
    answer: str
    sources: list[SourceResponse]
    conflicts: list[ConflictResponse]
    steps: list[InvestigationStepResponse]
