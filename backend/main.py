"""FastAPI app: composition root.

This file's only job is to build the app: create it, configure CORS and
security headers, wire up rate limiting and error handling, and include the
routers that actually define the endpoints (see interfaces/api/routers/).
All the actual business logic lives in application/*.py, and all the actual
endpoint definitions live in interfaces/api/routers/*.py - main.py just
assembles them.

Run locally with:
    uvicorn main:app --reload

On Render this is started with:
    alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT

(See ARCHITECTURE.md for why a migration step was added and what you need
to do once, by hand, before the first deploy of this refactored version.)
"""

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config import settings
from interfaces.api.error_handlers import register_error_handlers
from interfaces.api.rate_limit import limiter
from interfaces.api.routers.auth_router import router as auth_router
from interfaces.api.routers.expenses_router import router as expenses_router

app = FastAPI(title="Personal Expense Tracker API")

# ---------------------------------------------------------------------------
# Rate limiting (slowapi) - see interfaces/api/rate_limit.py for the Limiter
# instance and interfaces/api/routers/auth_router.py for where it's applied.
# Registering the exception handler here means exceeding a limit returns a
# normal JSON 429 response instead of an unhandled exception.
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Domain error -> HTTP response mapping (see interfaces/api/error_handlers.py
# and domain/errors.py).
# ---------------------------------------------------------------------------
register_error_handlers(app)

# ---------------------------------------------------------------------------
# CORS
#
# Allow the React frontend (a different origin) to call this API. Set
# FRONTEND_ORIGIN to your deployed frontend URL, e.g.
# https://my-expense-tracker.onrender.com
#
# Security note: browsers allow `allow_origins=["*"]` (any website) together
# with `allow_credentials=True` (send/accept cookies or Authorization
# headers) to be combined, but doing so is a real risk - it would mean ANY
# website could make credentialed requests to this API on behalf of a
# visitor. So: if FRONTEND_ORIGIN isn't set to a specific origin, we still
# allow "*" (so the API is reachable, e.g. for quick testing) but we turn
# credentials OFF. Once you set a real FRONTEND_ORIGIN, both a specific
# origin and credentials are enabled, same as before this change.
# ---------------------------------------------------------------------------
if settings.frontend_origin == "*":
    print(
        "WARNING: FRONTEND_ORIGIN is not set to a specific origin. "
        "Allowing all origins WITHOUT credentials. Set FRONTEND_ORIGIN to your "
        "deployed frontend's URL in production to allow authenticated requests."
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------------
# Security headers
#
# These headers tell browsers to be stricter about how they handle our
# responses, closing off a few classes of attack that don't involve any bug
# in our own code:
# - X-Content-Type-Options: nosniff - stops the browser from "guessing" a
#   different content type than we declared, which can otherwise be abused
#   to run a JSON response as if it were JavaScript/HTML.
# - X-Frame-Options: DENY - stops this API's responses from being embedded
#   in an <iframe> on another site (clickjacking protection).
# - Referrer-Policy: strict-origin-when-cross-origin - avoids leaking full
#   URLs (which might contain sensitive query params) to third-party sites
#   via the Referer header.
# - Strict-Transport-Security - tells the browser "always use HTTPS for this
#   site from now on", preventing downgrade attacks. Only sent when the
#   request actually arrived over HTTPS: Render terminates TLS at its edge
#   and forwards plain HTTP internally, so we check X-Forwarded-Proto (set
#   by Render's proxy) as well as the request's own scheme.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    if is_https:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

    return response


@app.get("/")
def health_check():
    """Simple endpoint so Render (and you) can check the API is alive."""
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(expenses_router)
