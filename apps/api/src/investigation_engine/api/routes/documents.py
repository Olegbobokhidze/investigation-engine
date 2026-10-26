from typing import Annotated

import structlog
from fastapi import APIRouter, Query, Request, Response, UploadFile, status

from investigation_engine.api.dependencies import DocumentServiceDependency
from investigation_engine.api.schemas.base import ErrorDetail
from investigation_engine.api.schemas.documents import (
    DocumentPageResponse,
    DocumentResponse,
    DuplicateUploadResult,
    FailedUploadResult,
    IndexedUploadResult,
    UploadResponse,
    UploadResult,
)
from investigation_engine.core.config import Settings
from investigation_engine.core.errors import (
    AppError,
    DuplicateDocumentError,
    FileTooLargeError,
    InvalidInputError,
)

router = APIRouter(prefix="/documents", tags=["documents"])
log = structlog.get_logger()

MAX_FILES_PER_UPLOAD = 20


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Reads at most `max_bytes` + 1 bytes, so an oversized file is rejected without
    being held in memory in full."""
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        limit_mb = max_bytes // 1_000_000
        raise FileTooLargeError(f"The file is larger than {limit_mb} MB.")
    return content


@router.get("")
async def list_documents(
    service: DocumentServiceDependency,
    search: Annotated[str, Query(max_length=200)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> DocumentPageResponse:
    documents, total = await service.list_documents(search.strip(), page, page_size)
    return DocumentPageResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("")
async def upload_documents(
    request: Request, service: DocumentServiceDependency, files: list[UploadFile]
) -> UploadResponse:
    """Indexes each file independently: one bad file doesn't fail the others."""
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise InvalidInputError(f"Upload at most {MAX_FILES_PER_UPLOAD} files at a time.")
    settings: Settings = request.app.state.settings

    results: list[UploadResult] = []
    for file in files:
        file_name = file.filename or "untitled"
        try:
            content = await _read_limited(file, settings.max_upload_bytes)
            document = await service.upload(content, file_name)
            results.append(
                IndexedUploadResult(
                    file_name=file_name, document=DocumentResponse.model_validate(document)
                )
            )
        except DuplicateDocumentError as error:
            results.append(
                DuplicateUploadResult(
                    file_name=file_name, duplicate_of_id=error.existing_document_id
                )
            )
        except AppError as error:
            results.append(
                FailedUploadResult(
                    file_name=file_name,
                    error=ErrorDetail(code=error.code, message=error.message),
                )
            )
        except Exception:
            # An unexpected failure on one file must not fail the whole upload; the details
            # go to the log, the user gets a generic message.
            log.exception("document_upload_failed", file_name=file_name)
            results.append(
                FailedUploadResult(
                    file_name=file_name,
                    error=ErrorDetail(
                        code="internal_error", message="Couldn't index this file. Please try again."
                    ),
                )
            )
    return UploadResponse(results=results)


@router.put("/{document_id}")
async def replace_document(
    document_id: str, request: Request, service: DocumentServiceDependency, file: UploadFile
) -> DocumentResponse:
    settings: Settings = request.app.state.settings
    content = await _read_limited(file, settings.max_upload_bytes)
    document = await service.replace(document_id, content, file.filename or "untitled")
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, service: DocumentServiceDependency) -> Response:
    await service.delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
