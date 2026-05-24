"""Service de Category (S04-T03)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.categories.models import Category
from app.categories.repository import CategoryRepository
from app.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

    def list_for_user(self, user_id: int) -> list[Category]:
        return self.repo.list_by_user(user_id)

    def get_for_user(self, user_id: int, category_id: int) -> Category | None:
        return self.repo.get_for_user(user_id, category_id)

    def create_for_user(self, user_id: int, payload: CategoryCreate) -> Category:
        category = Category(
            user_id=user_id,
            name=payload.name,
            type=payload.type,
            color=payload.color,
            icon=payload.icon,
            is_default=False,  # categorias criadas pelo usuario nunca sao default
        )
        return self.repo.add(category)

    def update_for_user(
        self, user_id: int, category_id: int, payload: CategoryUpdate
    ) -> Category | None:
        category = self.repo.get_for_user(user_id, category_id)
        if category is None:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        return self.repo.save(category)

    def delete_for_user(self, user_id: int, category_id: int) -> bool:
        category = self.repo.get_for_user(user_id, category_id)
        if category is None:
            return False
        # NOTA (S05): apos a tabela de transacoes existir, bloquear delete
        # de category padrao com transacoes associadas.
        self.repo.delete(category)
        return True
