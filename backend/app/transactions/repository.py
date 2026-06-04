"""Repository de Transaction (S05-T03)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.transactions.models import Transaction, TransactionType


@dataclass
class TransactionFilters:
    date_from: date_type | None = None
    date_to: date_type | None = None
    account_id: int | None = None
    category_id: int | None = None
    type: TransactionType | None = None
    search: str | None = None  # ilike na description


_ALLOWED_ORDER = {
    "date": Transaction.date,
    "-date": Transaction.date.desc(),
    "amount": Transaction.amount,
    "-amount": Transaction.amount.desc(),
    "created_at": Transaction.created_at,
    "-created_at": Transaction.created_at.desc(),
}


class TransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_for_user(self, user_id: int, txn_id: int) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.user_id == user_id, Transaction.id == txn_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def _base_stmt(self, user_id: int, filters: TransactionFilters):
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if filters.date_from is not None:
            stmt = stmt.where(Transaction.date >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(Transaction.date <= filters.date_to)
        if filters.account_id is not None:
            stmt = stmt.where(Transaction.account_id == filters.account_id)
        if filters.category_id is not None:
            stmt = stmt.where(Transaction.category_id == filters.category_id)
        if filters.type is not None:
            stmt = stmt.where(Transaction.type == filters.type)
        if filters.search:
            stmt = stmt.where(Transaction.description.ilike(f"%{filters.search}%"))
        return stmt

    async def count(self, user_id: int, filters: TransactionFilters) -> int:
        stmt = self._base_stmt(user_id, filters)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return int((await self.db.execute(count_stmt)).scalar_one())

    async def list_paginated(
        self,
        user_id: int,
        filters: TransactionFilters,
        page: int,
        page_size: int,
        order_by: str = "-date",
    ) -> list[Transaction]:
        order_expr = _ALLOWED_ORDER.get(order_by, _ALLOWED_ORDER["-date"])
        stmt = (
            self._base_stmt(user_id, filters)
            .order_by(order_expr, Transaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_by_user(self, user_id: int) -> list[Transaction]:
        """Compatibilidade: lista sem filtros, com ordem padrao."""
        return await self.list_paginated(user_id, TransactionFilters(), page=1, page_size=10_000)
