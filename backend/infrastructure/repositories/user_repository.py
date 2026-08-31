"""All database queries involving the User table, in one place.

Before this refactor, these queries were written inline in main.py and
auth.py (e.g. `db.query(models.User).filter(models.User.email == ...)`
appeared three separate times). Collecting them here means:

- the application layer (application/auth_service.py) doesn't need to know
  any SQLAlchemy query syntax, just "give me the user with this email", and
- if we ever change how users are stored, only this file needs to change.
"""

from typing import Optional

from sqlalchemy.orm import Session

from infrastructure.db.models import User


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create(
    db: Session,
    email: str,
    name: str,
    hashed_password: Optional[str] = None,
    google_id: Optional[str] = None,
) -> User:
    user = User(email=email, name=name, hashed_password=hashed_password, google_id=google_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def link_google_id(db: Session, user: User, google_id: str) -> User:
    """Attach a Google account id to a user who originally signed up with a
    password, so they can also sign in with Google from now on."""
    user.google_id = google_id
    db.commit()
    db.refresh(user)
    return user
