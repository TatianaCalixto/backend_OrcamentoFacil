"""Testes do model Category (S04-T01)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.users.models import User


def _make_user() -> int:
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        return u.id


def test_categoria_basica() -> None:
    user_id = _make_user()
    with SessionLocal() as db:
        c = Category(
            user_id=user_id,
            name="Alimentacao",
            type=CategoryType.EXPENSE,
            color="#ff0000",
            icon="utensils",
            is_default=True,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        assert c.id is not None
        assert c.is_default is True


def test_categoria_user_id_invalido_quebra_fk() -> None:
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Category(
                user_id=99999,
                name="Fantasma",
                type=CategoryType.EXPENSE,
            )
        )
        db.commit()


def test_categoria_aplica_defaults() -> None:
    user_id = _make_user()
    with SessionLocal() as db:
        c = Category(user_id=user_id, name="Lazer", type=CategoryType.EXPENSE)
        db.add(c)
        db.commit()
        db.refresh(c)
        assert c.color == "#888888"
        assert c.icon == "circle"
        assert c.is_default is False
