"""Service de Budget — calculo de uso e alertas (S06-T02)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.budgets.models import Budget
from app.budgets.repository import BudgetRepository
from app.budgets.schemas import (
    BudgetCreate,
    BudgetStatus,
    BudgetUpdate,
    BudgetWithUsage,
    status_for,
)
from app.categories.models import Category
from app.transactions.models import Transaction, TransactionType


class BudgetOwnershipError(Exception):
    """Categoria nao pertence ao usuario."""


class BudgetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BudgetRepository(db)

    # ----------------- ownership -----------------

    def _category_of(self, user_id: int, category_id: int) -> Category:
        cat = self.db.get(Category, category_id)
        if cat is None or cat.user_id != user_id:
            raise BudgetOwnershipError("category nao pertence ao usuario")
        return cat

    # ----------------- calculo -----------------

    def calculate_usage(self, budget: Budget) -> BudgetWithUsage:
        first_day = date(budget.year, budget.month, 1)
        last_day = date(budget.year, budget.month, monthrange(budget.year, budget.month)[1])

        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == budget.user_id,
            Transaction.category_id == budget.category_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= first_day,
            Transaction.date <= last_day,
        )
        total = self.db.execute(stmt).scalar_one()
        used = Decimal(total) if total is not None else Decimal("0")

        if budget.limit_amount > 0:
            percent = (used / budget.limit_amount * Decimal("100")).quantize(Decimal("0.01"))
        else:  # nunca acontece (CHECK > 0), mas defensivo
            percent = Decimal("0")

        return BudgetWithUsage(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            month=budget.month,
            year=budget.year,
            limit_amount=budget.limit_amount,
            used_amount=used,
            percent_used=percent,
            status=status_for(percent),
        )

    # ----------------- list/get/create/update -----------------

    def list_with_usage_for_month(
        self, user_id: int, month: int, year: int
    ) -> list[BudgetWithUsage]:
        return [
            self.calculate_usage(b) for b in self.repo.list_for_user_month(user_id, month, year)
        ]

    def get_with_usage(self, user_id: int, budget_id: int) -> BudgetWithUsage | None:
        b = self.repo.get_for_user(user_id, budget_id)
        if b is None:
            return None
        return self.calculate_usage(b)

    def create_for_user(self, user_id: int, payload: BudgetCreate) -> Budget:
        self._category_of(user_id, payload.category_id)
        budget = Budget(
            user_id=user_id,
            category_id=payload.category_id,
            month=payload.month,
            year=payload.year,
            limit_amount=payload.limit_amount,
        )
        return self.repo.add(budget)

    def update_for_user(self, user_id: int, budget_id: int, payload: BudgetUpdate) -> Budget | None:
        b = self.repo.get_for_user(user_id, budget_id)
        if b is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        for k, v in updates.items():
            setattr(b, k, v)
        return self.repo.save(b)


# helper para o router checar status enum no payload
__all__ = ["BudgetOwnershipError", "BudgetService", "BudgetStatus"]
