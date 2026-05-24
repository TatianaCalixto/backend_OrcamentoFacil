"""Model Category (S04-T01)."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CategoryType(StrEnum):
    INCOME = "income"  # receita
    EXPENSE = "expense"  # despesa


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type"), nullable=False
    )
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#888888")
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="circle")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<Category id={self.id} user_id={self.user_id} name={self.name!r}>"
