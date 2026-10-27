"""Domain exception hierarchy.

Services raise these; the API layer maps them to HTTP responses in one place,
so no route handler needs its own try/except.
"""


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class DuplicateDocumentError(AppError):
    """The content is already indexed as another document."""

    status_code = 409
    code = "duplicate_document"

    def __init__(self, existing_document_id: str) -> None:
        super().__init__(f"The same content is already indexed as {existing_document_id}.")
        self.existing_document_id = existing_document_id


class InvalidInputError(AppError):
    status_code = 422
    code = "invalid_input"


class UnsupportedFormatError(InvalidInputError):
    code = "unsupported_format"


class FileTooLargeError(InvalidInputError):
    status_code = 413
    code = "file_too_large"


class UnreadableFileError(InvalidInputError):
    """The file has a supported extension but its content can't be parsed."""

    code = "unreadable_file"


class EmptyDocumentError(InvalidInputError):
    """The file parsed, but contains no text to index (e.g. a scanned PDF)."""

    code = "empty_document"


class NotConfiguredError(AppError):
    """A feature needs a setting that isn't set (e.g. the LLM API key in local dev)."""

    status_code = 503
    code = "not_configured"


class UpstreamError(AppError):
    """An external dependency (LLM, vector store) failed after retries."""

    status_code = 502
    code = "upstream_error"
