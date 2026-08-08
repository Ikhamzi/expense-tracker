"""Pydantic models (schemas) used to validate requests and shape responses.

These are separate from the SQLAlchemy models in models.py: models.py
describes database tables, this file describes the JSON that goes in and
out of the API.
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
    name: str


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
    category: str
    description: Optional[str] = None
    date: date


class ExpenseUpdate(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str
    description: Optional[str] = None
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
