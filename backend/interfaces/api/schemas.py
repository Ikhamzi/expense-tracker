"""Pydantic models (schemas) used to validate requests and shape responses.

These are separate from the SQLAlchemy models in infrastructure/db/models.py:
that file describes database tables, this file describes the JSON that goes
in and out of the API.

Unchanged from the old top-level schemas.py, except for one addition: three
fields now have a `max_length` so a client can't send an unreasonably huge
string (name, category, description). Field names, types, and every other
existing constraint (password min_length=6, amount gt=0) are exactly the
same as before, so this does not change any currently-valid request.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    # The ID token that Google Identity Services returns to the frontend
    # after the user signs in with their Google account.
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Expense schemas
# ---------------------------------------------------------------------------


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    date: date


class ExpenseUpdate(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    date: date


class ExpenseOut(BaseModel):
    id: int
    amount: Decimal
    category: str
    description: Optional[str] = None
    date: date
    created_at: datetime

    class Config:
        # Lets us return a SQLAlchemy Expense object directly and have
        # Pydantic read its attributes instead of requiring a dict.
        from_attributes = True


class CategoryTotal(BaseModel):
    category: str
    total: Decimal


class SummaryOut(BaseModel):
    month: str
    total: Decimal
    by_category: list[CategoryTotal]
