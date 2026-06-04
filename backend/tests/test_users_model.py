"""Testes do model User (S02-T01)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.users.models import User


async def test_insercao_de_user_persiste_campos() -> None:
    async with SessionLocal() as db:
        u = User(name="Ana", email="ana@ex.com", password_hash="hash")
        db.add(u)
        await db.commit()
        await db.refresh(u)
        assert u.id is not None
        assert u.created_at is not None
        assert u.email == "ana@ex.com"


async def test_email_duplicado_quebra_unique() -> None:
    async with SessionLocal() as db:
        db.add(User(name="A", email="dup@ex.com", password_hash="h"))
        await db.commit()

    async with SessionLocal() as db:
        db.add(User(name="B", email="dup@ex.com", password_hash="h2"))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_email_unico_case_sensitive_default() -> None:
    """Por padrao, sqlite distingue caixa; teste documenta o comportamento atual.
    Normalizacao de email (lowercasing) e regra de negocio que vira em S02-T04."""
    async with SessionLocal() as db:
        db.add(User(name="A", email="caps@ex.com", password_hash="h"))
        await db.commit()
    async with SessionLocal() as db:
        # email com caixa diferente NAO bate o unique no sqlite default
        db.add(User(name="B", email="CAPS@ex.com", password_hash="h2"))
        await db.commit()
