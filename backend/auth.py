"""Everything related to authentication:

- hashing / checking passwords with passlib (bcrypt)
- creating / decoding our own session JWTs with python-jose
- verifying Google ID tokens with google-auth
- a FastAPI dependency (get_current_user) that every expense endpoint uses
"""

import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Our own session JWTs (separate from Google's tokens)
# ---------------------------------------------------------------------------

# Secret key used to sign session tokens. Set a long random value in
# production via the JWT_SECRET_KEY environment variable.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(user_id: int) -> str:
    """Create a signed JWT that encodes the user's id in the 'sub' claim."""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Tells FastAPI to expect "Authorization: Bearer <token>" on protected routes.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Decode the JWT from the Authorization header and load the matching
    User row. Every expense endpoint depends on this, which is what
    guarantees a user can only ever see or change their own data."""
    invalid_token_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise invalid_token_error
    except JWTError:
        raise invalid_token_error

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise invalid_token_error
    return user


# ---------------------------------------------------------------------------
# Google Sign-In
# ---------------------------------------------------------------------------

# The OAuth client ID of our app, from the Google Cloud Console. Google
# tokens are only accepted if they were issued for this exact client id.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token's signature and audience, and return its
    payload (contains 'email', 'name', 'sub', ...). Raises ValueError if
    the token is invalid, expired, or was issued for a different app."""
    return google_id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
