"""SQLAlchemy table models: users and expenses."""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)

    # Nullable because a user who signs in with Google never sets a password.
    hashed_password = Column(String, nullable=True)

    # Nullable because a user who signs up with email/password has no Google id
    # until (if ever) they link their account.
    google_id = Column(String, unique=True, nullable=True)

    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    expenses = relationship("Expense", back_populates="owner", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="expenses")

    __table_args__ = (
        # Almost every query is "this user's expenses in this month", so a
        # combined index on (user_id, date) makes those queries fast.
        Index("ix_expenses_user_id_date", "user_id", "date"),
    )
