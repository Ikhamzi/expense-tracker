"""Centralized, validated application configuration.

Every other module reads settings from the `settings` object defined here
instead of calling `os.environ` directly. That gives us one place where:

- required environment variables are checked at startup (fail fast with a
  clear message instead of a confusing error deep inside a request), and
- a production deploy can refuse to boot if it's misconfigured in a way
  that would be a real security problem (see the JWT_SECRET_KEY check
  below).

The environment variable names are unchanged from before this refactor
(DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID, FRONTEND_ORIGIN) - pydantic
-settings matches them to the lowercase field names automatically.
"""

from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# The same default that auth.py used to fall back to for local development.
# Kept here (not just re-typed in the production check below) so there's a
# single source of truth for "this is the insecure placeholder value".
_DEV_JWT_SECRET_DEFAULT = "dev-secret-change-me"


class Settings(BaseSettings):
    # The Neon Postgres connection string, e.g.
    # postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require
    # Required - there's no sensible default for a database URL.
    database_url: str

    # Secret key used to sign our own session JWTs. Has a default so the app
    # still runs out of the box for local development, but see the
    # production check below - this default is not allowed in production.
    jwt_secret_key: str = _DEV_JWT_SECRET_DEFAULT

    # Google OAuth client ID used to verify "Sign in with Google" tokens.
    google_client_id: str = ""

    # The deployed frontend's origin, used for CORS. Defaults to "*" (any
    # origin) for local development; see main.py for what that means for
    # cookies/credentials.
    frontend_origin: str = "*"

    # "development" (default) or "production". Set ENV=production on Render.
    env: str = "development"

    # Reads a local .env file if present (same behavior as the old
    # `load_dotenv()` call in database.py), and does nothing if it's absent
    # (e.g. on Render, where env vars are set in the dashboard instead).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def _load_settings() -> Settings:
    try:
        return Settings()
    except PydanticValidationError as exc:
        missing = sorted(
            {str(error["loc"][0]).upper() for error in exc.errors() if error["type"] == "missing"}
        )
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Set them in a .env file (see .env.example) for local development, "
                + "or in the Render dashboard's Environment tab for a deployed service."
            ) from exc
        # Some other kind of validation error - re-raise with the original
        # (still fairly readable) pydantic message rather than hiding it.
        raise RuntimeError(f"Invalid application configuration: {exc}") from exc


settings = _load_settings()

# Refuse to boot a production deployment that's still using the insecure
# development default secret key - if an attacker knows this default (it's
# public, right here in the source code) they could forge login tokens for
# any user.
if settings.env == "production" and settings.jwt_secret_key == _DEV_JWT_SECRET_DEFAULT:
    raise RuntimeError(
        "Refusing to start: ENV=production but JWT_SECRET_KEY is still the default "
        f'development value ("{_DEV_JWT_SECRET_DEFAULT}"). Set a long random secret via the '
        "JWT_SECRET_KEY environment variable before deploying to production."
    )
