"""Expense endpoints: GET/POST /expenses, PUT/DELETE /expenses/{expense_id},
GET /expenses/summary.

Same paths, methods, and response models as the old main.py. Every route
depends on get_current_user, and the actual list/create/update/delete/
summary logic now lives in application/expense_service.py - this file only
translates HTTP <-> Python calls.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from application import expense_service
from infrastructure.db.base import get_db
from infrastructure.db.models import User
from interfaces.api import schemas
from interfaces.api.deps import get_current_user

router = APIRouter(prefix="/expenses")


@router.get("", response_model=list[schemas.ExpenseOut])
def list_expenses(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's expenses, newest first. Pass ?month=YYYY-MM
    to only get expenses from that month."""
    return expense_service.list_expenses(db, current_user.id, month)


@router.post("", response_model=schemas.ExpenseOut)
def create_expense(
    body: schemas.ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new expense for the current user."""
    return expense_service.create_expense(db, current_user.id, body.model_dump())


@router.put("/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    body: schemas.ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the current user's expenses."""
    return expense_service.update_expense(db, current_user.id, expense_id, body.model_dump())


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the current user's expenses."""
    expense_service.delete_expense(db, current_user.id, expense_id)
    return {"ok": True}


@router.get("/summary", response_model=schemas.SummaryOut)
def expense_summary(
    month: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the total spent and a per-category breakdown for one month."""
    month, total, rows = expense_service.get_summary(db, current_user.id, month)
    by_category = [schemas.CategoryTotal(category=category, total=row_total) for category, row_total in rows]
    return schemas.SummaryOut(month=month, total=total, by_category=by_category)
