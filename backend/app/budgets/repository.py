"""Repository de Budget (S06-T02)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.budgets.models import Budget


class BudgetRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_user(self, user_id: int, budget_id: int) -> Budget | None:
        stmt = select(Budget).where(Budget.user_id == user_id, Budget.id == budget_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_user_month(
        self,
        user_id: int,
        month: int,
        year: int,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Budget]:
        # order_by(id): mais antigos primeiro (S24-T06). Paginacao opcional;
        # default page_size=50 cobre os casos reais (poucos budgets por mes).
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
            .order_by(Budget.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def add(self, budget: Budget) -> Budget:
        self.db.add(budget)
        await self.db.flush()
        await self.db.refresh(budget)
        return budget

    async def save(self, budget: Budget) -> Budget:
        await self.db.flush()
        await self.db.refresh(budget)
        return budget
