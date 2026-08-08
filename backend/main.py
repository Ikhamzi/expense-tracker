"""FastAPI app: auth endpoints + expense endpoints.

Run locally with:
    uvicorn main:app --reload

On Render this is started with:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import os
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_google_token,
    verify_password,
)
from database import Base, engine, get_db

# Create the users/expenses tables if they don't exist yet. For a hobby
# project this is simpler than running migrations by hand.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Expense Tracker API")

# Allow the React frontend (a different origin) to call this API.
# Set FRONTEND_ORIGIN to your deployed frontend URL, e.g.
# https://my-expense-tracker.onrender.com
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    """Simple endpoint so Render (and you) can check the API is alive."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/signup", response_model=schemas.TokenResponse)
def signup(body: schemas.SignupRequest, db: Session = Depends(get_db)):
    """Create a new account with an email + password and return a login token."""
    existing_user = db.query(models.User).filter(models.User.email == body.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered")

    user = models.User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Check an email + password and return a login token if they match."""
    user = db.query(models.User).filter(models.User.email == body.email).first()

    # Same error for "no such user" and "wrong password" so we don't leak
    # which emails are registered.
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)


@app.post("/auth/google", response_model=schemas.TokenResponse)
def google_auth(body: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token from the frontend, then log in the matching
    user, creating a new account the first time we see their email."""
    try:
        payload = verify_google_token(body.id_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_id = payload["sub"]
    email = payload["email"]
    name = payload.get("name", email)

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        # First time this email has signed in - create a new account.
        user = models.User(email=email, name=name, google_id=google_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.google_id:
        # They already had a password account with this email - link it.
        user.google_id = google_id
        db.commit()

    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Expense endpoints
#
# Every one of these depends on get_current_user, and every database query
# filters by that user's id, so a user can never read or modify anyone
# else's expenses.
# ---------------------------------------------------------------------------


def _month_to_date_range(month: str) -> tuple[date, date]:
    """Turn 'YYYY-MM' into (first day of month, last day of month)."""
    try:
        year_str, month_str = month.split("-")
        year, mon = int(year_str), int(month_str)
        first_day = date(year, mon, 1)
        last_day = date(year, mon, monthrange(year, mon)[1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    return first_day, last_day


@app.get("/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    month: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's expenses, newest first. Pass ?month=YYYY-MM
    to only get expenses from that month."""
    query = db.query(models.Expense).filter(models.Expense.user_id == current_user.id)

    if month:
        first_day, last_day = _month_to_date_range(month)
        query = query.filter(models.Expense.date.between(first_day, last_day))

    return query.order_by(models.Expense.date.desc()).all()


@app.post("/expenses", response_model=schemas.ExpenseOut)
def create_expense(
    body: schemas.ExpenseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new expense for the current user."""
    expense = models.Expense(user_id=current_user.id, **body.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    body: schemas.ExpenseUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the current user's expenses."""
    expense = (
        db.query(models.Expense)
        .filter(models.Expense.id == expense_id, models.Expense.user_id == current_user.id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    for field, value in body.model_dump().items():
        setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/expenses/{expense_id}")
def delete_expense(
    expense_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the current user's expenses."""
    expense = (
        db.query(models.Expense)
        .filter(models.Expense.id == expense_id, models.Expense.user_id == current_user.id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return {"ok": True}


@app.get("/expenses/summary", response_model=schemas.SummaryOut)
def expense_summary(
    month: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the total spent and a per-category breakdown for one month."""
    first_day, last_day = _month_to_date_range(month)

    rows = (
        db.query(models.Expense.category, func.sum(models.Expense.amount))
        .filter(
            models.Expense.user_id == current_user.id,
            models.Expense.date.between(first_day, last_day),
        )
        .group_by(models.Expense.category)
        .all()
    )

    by_category = [schemas.CategoryTotal(category=category, total=total) for category, total in rows]
    total = sum((row.total for row in by_category), start=Decimal("0"))

    return schemas.SummaryOut(month=month, total=total, by_category=by_category)
