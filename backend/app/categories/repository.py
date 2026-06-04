"""Repository de Category (S04-T03)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.categories.models import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_user(self, user_id: int) -> list[Category]:
        stmt = select(Category).where(Category.user_id == user_id).order_by(Category.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_for_user(self, user_id: int, category_id: int) -> Category | None:
        stmt = select(Category).where(Category.user_id == user_id, Category.id == category_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def save(self, category: Category) -> Category:
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.flush()
