"""Domain-level errors.

These are plain Python exceptions with no knowledge of FastAPI, HTTP status
codes, or JSON. The application layer (application/*.py) raises them when a
business rule is broken. The interface layer
(interfaces/api/error_handlers.py) is the only place that knows how to turn
them into an HTTP response - that keeps the "what went wrong" logic separate
from the "how do we tell the client" logic.
"""


class DomainError(Exception):
    """Base class for every error raised by the domain/application layers."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested record doesn't exist (or doesn't belong to
    the current user, which we treat the same as "doesn't exist" so we never
    reveal that another user's data exists). Maps to HTTP 404."""


class ValidationError(DomainError):
    """Raised when input fails a business rule that goes beyond what
    Pydantic's field-level validation already checks (e.g. "month must be in
    YYYY-MM format"). Maps to HTTP 400."""


class ConflictError(DomainError):
    """Raised when a request conflicts with existing data (e.g. signing up
    with an email that's already registered). Maps to HTTP 400, matching the
    status code this API has always used for that case."""
