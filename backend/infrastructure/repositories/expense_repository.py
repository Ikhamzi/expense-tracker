"""All database queries involving the Expense table, in one place.

Same idea as user_repository.py: every query is written here once, and the
application layer (application/expense_service.py) calls these functions by
name instead of writing SQLAlchemy filters inline. Every function here that
reads or writes an expense takes a `user_id` and filters by it, which is
what guarantees a user can never see or change another user's expenses.
"""

from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from infrastructure.db.models import Expense


def list_for_user(
    db: Session,
    user_id: int,
    month_range: Optional[tuple[date, date]] = None,
) -> list[Expense]:
    """List a user's expenses, newest first. If `month_range` is given
    (first_day, last_day), only expenses dated within that range are
    included."""
    query = db.query(Expense).filter(Expense.user_id == user_id)

    if month_range is not None:
        first_day, last_day = month_range
        query = query.filter(Expense.date.between(first_day, last_day))

    return query.order_by(Expense.date.desc()).all()


def get_by_id_for_user(db: Session, expense_id: int, user_id: int) -> Optional[Expense]:
    return (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.user_id == user_id)
        .first()
    )


def create(db: Session, user_id: int, data: dict) -> Expense:
    expense = Expense(user_id=user_id, **data)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def update(db: Session, expense: Expense, data: dict) -> Expense:
    for field, value in data.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


def delete(db: Session, expense: Expense) -> None:
    db.delete(expense)
    db.commit()


def sum_by_category_for_month(
    db: Session, user_id: int, first_day: date, last_day: date
) -> list[tuple[str, object]]:
    """Return (category, total_amount) rows for one user's expenses in one
    month, one row per category."""
    return (
        db.query(Expense.category, func.sum(Expense.amount))
        .filter(
            Expense.user_id == user_id,
            Expense.date.between(first_day, last_day),
        )
        .group_by(Expense.category)
        .all()
    )
