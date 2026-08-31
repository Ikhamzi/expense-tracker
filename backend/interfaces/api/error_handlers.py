"""Maps domain errors (domain/errors.py) to HTTP responses.

The application layer raises plain Python exceptions like NotFoundError
without knowing anything about HTTP. This is the one place that translates
"what went wrong" into "what status code and JSON body does the client
get" - using the exact same `{"detail": "..."}` shape FastAPI's own
HTTPException already produces, so clients (including the live frontend)
see no difference.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.errors import ConflictError, NotFoundError, ValidationError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(ConflictError)
    async def handle_conflict(request: Request, exc: ConflictError):
        return JSONResponse(status_code=400, content={"detail": exc.message})
