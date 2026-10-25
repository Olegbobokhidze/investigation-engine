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


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class UnsupportedFormatError(ValidationError):
    code = "unsupported_format"


class UpstreamError(AppError):
    """An external dependency (LLM, vector store) failed after retries."""

    status_code = 502
    code = "upstream_error"
