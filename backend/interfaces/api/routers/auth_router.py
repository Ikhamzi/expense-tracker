"""Auth endpoints: POST /auth/signup, /auth/login, /auth/google.

Same paths, methods, and response models as the old main.py. The actual
signup/login/Google logic now lives in application/auth_service.py; this
file only translates HTTP <-> Python calls, and applies rate limiting.

Rate limiting: each of these three endpoints is limited to 10 requests per
minute per client IP address (via slowapi). Login and signup are common
targets for password-guessing and account-creation-spam bots, so limiting
how fast one IP can hit these specific endpoints makes those attacks much
slower without affecting normal users (nobody logs in 10+ times a minute).
slowapi requires the decorated function to take a `request: Request`
parameter, which is why these handlers now have one even though they don't
otherwise use it.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from application import auth_service
from infrastructure.db.base import get_db
from interfaces.api import schemas
from interfaces.api.rate_limit import limiter

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def signup(request: Request, body: schemas.SignupRequest, db: Session = Depends(get_db)):
    """Create a new account with an email + password and return a login token."""
    token = auth_service.signup(db, email=body.email, password=body.password, name=body.name)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Check an email + password and return a login token if they match."""
    token = auth_service.login(db, email=body.email, password=body.password)
    return schemas.TokenResponse(access_token=token)


@router.post("/google", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def google_auth(request: Request, body: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token from the frontend, then log in the matching
    user, creating a new account the first time we see their email."""
    token = auth_service.google_auth(db, id_token=body.id_token)
    return schemas.TokenResponse(access_token=token)
