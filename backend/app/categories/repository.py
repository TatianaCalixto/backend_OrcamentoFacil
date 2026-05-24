"""Repository de Category (S04-T03)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categories.models import Category


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: int) -> list[Category]:
        stmt = select(Category).where(Category.user_id == user_id).order_by(Category.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_for_user(self, user_id: int, category_id: int) -> Category | None:
        stmt = select(Category).where(Category.user_id == user_id, Category.id == category_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, category: Category) -> Category:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def save(self, category: Category) -> Category:
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.commit()
