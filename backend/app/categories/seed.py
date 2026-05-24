"""Seed de categorias padrao por usuario (S04-T02)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.categories.models import Category, CategoryType

# (name, type, color, icon) — 8 categorias padrao
DEFAULT_CATEGORIES: list[tuple[str, CategoryType, str, str]] = [
    ("Alimentacao", CategoryType.EXPENSE, "#e74c3c", "utensils"),
    ("Transporte", CategoryType.EXPENSE, "#3498db", "car"),
    ("Saude", CategoryType.EXPENSE, "#2ecc71", "heart-pulse"),
    ("Educacao", CategoryType.EXPENSE, "#9b59b6", "book"),
    ("Moradia", CategoryType.EXPENSE, "#34495e", "house"),
    ("Lazer", CategoryType.EXPENSE, "#f39c12", "gamepad"),
    ("Assinaturas", CategoryType.EXPENSE, "#1abc9c", "repeat"),
    ("Outros", CategoryType.EXPENSE, "#95a5a6", "circle"),
]


def seed_default_categories(db: Session, user_id: int) -> list[Category]:
    """Cria as categorias padrao para um usuario recem-registrado.

    Idempotente: nao recria categorias que ja existam com mesmo name+user.
    """
    from sqlalchemy import select

    existentes = {
        row[0]
        for row in db.execute(
            select(Category.name).where(Category.user_id == user_id, Category.is_default.is_(True))
        ).all()
    }

    novas: list[Category] = []
    for name, ctype, color, icon in DEFAULT_CATEGORIES:
        if name in existentes:
            continue
        novas.append(
            Category(
                user_id=user_id,
                name=name,
                type=ctype,
                color=color,
                icon=icon,
                is_default=True,
            )
        )

    if novas:
        db.add_all(novas)
        db.commit()
        for c in novas:
            db.refresh(c)
    return novas
