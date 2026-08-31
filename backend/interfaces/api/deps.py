"""Shared FastAPI dependencies for the API layer.

get_current_user is used by every expense endpoint. It decodes the bearer
token, loads the matching user, and raises the exact same 401 ("Could not
validate credentials") the old top-level auth.py raised for any kind of
invalid token - expired, tampered with, or referring to a user that no
longer exists.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from infrastructure.db.base import get_db
from infrastructure.db.models import User
from infrastructure.repositories import user_repository
from infrastructure.security.tokens import decode_access_token

# Tells FastAPI to expect "Authorization: Bearer <token>" on protected routes.
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT from the Authorization header and load the matching
    User row. Every expense endpoint depends on this, which is what
    guarantees a user can only ever see or change their own data."""
    invalid_token_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise invalid_token_error
    except JWTError:
        raise invalid_token_error

    user = user_repository.get_by_id(db, int(user_id))
    if user is None:
        raise invalid_token_error
    return user
