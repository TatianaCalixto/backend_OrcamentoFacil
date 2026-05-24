"""Repository de Budget (S06-T02)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budgets.models import Budget


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, user_id: int, budget_id: int) -> Budget | None:
        stmt = select(Budget).where(Budget.user_id == user_id, Budget.id == budget_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user_month(self, user_id: int, month: int, year: int) -> list[Budget]:
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
            .order_by(Budget.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def add(self, budget: Budget) -> Budget:
        self.db.add(budget)
        self.db.commit()
        self.db.refresh(budget)
        return budget

    def save(self, budget: Budget) -> Budget:
        self.db.commit()
        self.db.refresh(budget)
        return budget
