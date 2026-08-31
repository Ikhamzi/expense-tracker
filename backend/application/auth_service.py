"""Auth use cases: signup, login, and Google sign-in.

This is the same logic that used to live directly inside the route handlers
in main.py. Moving it here means the route handlers (interfaces/api/routers
/auth_router.py) only deal with HTTP concerns (reading the request body,
returning the response), while this file deals with the actual business
logic, calling repositories and security helpers instead of touching the
database or JWT library directly.

Note on error handling: most business-rule failures in this app raise a
domain error (see domain/errors.py) that interfaces/api/error_handlers.py
turns into an HTTP response. Invalid login credentials and invalid Google
tokens are the exception - this API has always returned 401 for those, and
401 isn't one of the status codes our domain errors map to (only 404/400
are), so those two cases raise fastapi.HTTPException directly here, exactly
as main.py used to. This keeps the exact same status codes and messages the
live frontend already depends on.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from domain.errors import ConflictError
from infrastructure.repositories import user_repository
from infrastructure.security.google import verify_google_token
from infrastructure.security.passwords import hash_password, verify_password
from infrastructure.security.tokens import create_access_token


def signup(db: Session, email: str, password: str, name: str) -> str:
    """Create a new account with an email + password and return a login token."""
    existing_user = user_repository.get_by_email(db, email)
    if existing_user:
        raise ConflictError("Email is already registered")

    user = user_repository.create(db, email=email, name=name, hashed_password=hash_password(password))
    return create_access_token(user.id)


def login(db: Session, email: str, password: str) -> str:
    """Check an email + password and return a login token if they match."""
    user = user_repository.get_by_email(db, email)

    # Same error for "no such user" and "wrong password" so we don't leak
    # which emails are registered.
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return create_access_token(user.id)


def google_auth(db: Session, id_token: str) -> str:
    """Verify a Google ID token from the frontend, then log in the matching
    user, creating a new account the first time we see their email."""
    try:
        payload = verify_google_token(id_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    google_id = payload["sub"]
    email = payload["email"]
    name = payload.get("name", email)

    user = user_repository.get_by_email(db, email)
    if user is None:
        # First time this email has signed in - create a new account.
        user = user_repository.create(db, email=email, name=name, google_id=google_id)
    elif not user.google_id:
        # They already had a password account with this email - link it.
        user = user_repository.link_google_id(db, user, google_id)

    return create_access_token(user.id)
