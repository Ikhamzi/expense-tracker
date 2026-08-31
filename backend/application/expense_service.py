"""Expense use cases: list, create, update, delete, and monthly summary.

Same logic as the old route handlers in main.py, moved here so the route
handlers (interfaces/api/routers/expenses_router.py) only handle HTTP
concerns. Every function takes the current user's id and only ever
reads/writes that user's own expenses (via expense_repository, which
filters by user_id) - this is what guarantees a user can never see or
change anyone else's data.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from domain.entities import parse_month_range
from domain.errors import NotFoundError
from infrastructure.db.models import Expense
from infrastructure.repositories import expense_repository


def list_expenses(db: Session, user_id: int, month: Optional[str] = None) -> list[Expense]:
    """List the current user's expenses, newest first. If `month`
    (YYYY-MM) is given, only expenses from that month are returned."""
    month_range = parse_month_range(month) if month else None
    return expense_repository.list_for_user(db, user_id, month_range)


def create_expense(db: Session, user_id: int, data: dict) -> Expense:
    """Add a new expense for the current user."""
    return expense_repository.create(db, user_id, data)


def update_expense(db: Session, user_id: int, expense_id: int, data: dict) -> Expense:
    """Update one of the current user's expenses."""
    expense = expense_repository.get_by_id_for_user(db, expense_id, user_id)
    if not expense:
        raise NotFoundError("Expense not found")
    return expense_repository.update(db, expense, data)


def delete_expense(db: Session, user_id: int, expense_id: int) -> None:
    """Delete one of the current user's expenses."""
    expense = expense_repository.get_by_id_for_user(db, expense_id, user_id)
    if not expense:
        raise NotFoundError("Expense not found")
    expense_repository.delete(db, expense)


def get_summary(db: Session, user_id: int, month: str) -> tuple[str, Decimal, list[tuple[str, Decimal]]]:
    """Return (month, total, by_category) for one month, where by_category
    is a list of (category, total) pairs."""
    first_day, last_day = parse_month_range(month)
    rows = expense_repository.sum_by_category_for_month(db, user_id, first_day, last_day)
    total = sum((row_total for _category, row_total in rows), start=Decimal("0"))
    return month, total, rows
