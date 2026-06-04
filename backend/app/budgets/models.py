"""Model Budget (S06-T01)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    month: Mapped[int] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "category_id", "month", "year", name="uq_budgets_user_cat_month_year"
        ),
        # S24-T04: query real list_for_user_month filtra por (user_id, month, year).
        Index("ix_budgets_user_id_month_year", "user_id", "month", "year"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_budgets_month_range"),
        CheckConstraint("year BETWEEN 2000 AND 2100", name="ck_budgets_year_range"),
        CheckConstraint("limit_amount > 0", name="ck_budgets_limit_positive"),
    )

    def __repr__(self) -> str:
        return f"<Budget id={self.id} cat={self.category_id} {self.month:02d}/{self.year} limit={self.limit_amount}>"
