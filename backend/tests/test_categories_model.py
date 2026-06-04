"""Testes do model Category (S04-T01)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.users.models import User


async def _make_user() -> int:
    async with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        return u.id


async def test_categoria_basica() -> None:
    user_id = await _make_user()
    async with SessionLocal() as db:
        c = Category(
            user_id=user_id,
            name="Alimentacao",
            type=CategoryType.EXPENSE,
            color="#ff0000",
            icon="utensils",
            is_default=True,
        )
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.id is not None
        assert c.is_default is True


async def test_categoria_user_id_invalido_quebra_fk() -> None:
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.add(
                Category(
                    user_id=99999,
                    name="Fantasma",
                    type=CategoryType.EXPENSE,
                )
            )
            await db.commit()


async def test_categoria_aplica_defaults() -> None:
    user_id = await _make_user()
    async with SessionLocal() as db:
        c = Category(user_id=user_id, name="Lazer", type=CategoryType.EXPENSE)
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.color == "#888888"
        assert c.icon == "circle"
        assert c.is_default is False
