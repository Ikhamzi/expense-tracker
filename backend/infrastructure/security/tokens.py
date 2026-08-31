"""Creating and decoding our own session JWTs (separate from Google's
tokens, which are handled in infrastructure/security/google.py).

Behavior compared to the old top-level auth.py:
- SECRET_KEY and ALGORITHM now come from infrastructure.config.settings
  instead of reading os.environ directly.
- ACCESS_TOKEN_EXPIRE_MINUTES is unchanged (7 days).
- Two extra standard JWT claims are added when creating a token: "iat"
  (issued-at time) and "iss" (issuer). These don't change what a token
  grants access to, but they're good practice and make tokens easier to
  debug/audit (you can tell when a token was issued and that it came from
  this API). Decoding does NOT require these claims to be present, so
  tokens issued by the previous version of this API (before this change)
  keep working until they expire - nobody gets logged out by this change.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt

from infrastructure.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ISSUER = "expense-tracker-api"


def create_access_token(user_id: int) -> str:
    """Create a signed JWT that encodes the user's id in the 'sub' claim."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
        "iss": ISSUER,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a session JWT's signature and expiry, returning its
    payload. Raises jose.JWTError (via jwt.decode) if the token is invalid,
    expired, or tampered with - callers (see interfaces/api/deps.py) are
    responsible for turning that into an HTTP 401."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
