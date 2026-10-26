"""Request and response bodies for /documents. Mirrors apps/web/src/features/documents/types.ts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from investigation_engine.api.schemas.base import ApiModel, ErrorDetail
from investigation_engine.documents.models import DocumentOrigin, FileType


class DocumentResponse(ApiModel):
    id: str
    title: str
    file_type: FileType
    chunk_count: int
    origin: DocumentOrigin
    created_at: datetime


class DocumentPageResponse(ApiModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class IndexedUploadResult(ApiModel):
    file_name: str
    status: Literal["indexed"] = "indexed"
    document: DocumentResponse


class DuplicateUploadResult(ApiModel):
    file_name: str
    status: Literal["duplicate"] = "duplicate"
    duplicate_of_id: str


class FailedUploadResult(ApiModel):
    file_name: str
    status: Literal["failed"] = "failed"
    error: ErrorDetail


# Each file in an upload succeeds or fails on its own; `status` tells the variants apart.
type UploadResult = Annotated[
    IndexedUploadResult | DuplicateUploadResult | FailedUploadResult,
    Field(discriminator="status"),
]


class UploadResponse(ApiModel):
    results: list[UploadResult]
