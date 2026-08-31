"""Verifying Google ID tokens ("Sign in with Google"). Same logic as the old
top-level auth.py, reading GOOGLE_CLIENT_ID from infrastructure.config
instead of os.environ directly."""

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from infrastructure.config import settings


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token's signature and audience, and return its
    payload (contains 'email', 'name', 'sub', ...). Raises ValueError if
    the token is invalid, expired, or was issued for a different app."""
    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), settings.google_client_id
    )
