"""Testes do seed de categorias padrao (S04-T02)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.categories.models import Category
from app.categories.seed import DEFAULT_CATEGORIES, seed_default_categories
from app.database.session import SessionLocal
from app.main import app
from app.users.models import User

client = TestClient(app, raise_server_exceptions=False)


async def test_seed_cria_8_categorias_padrao_para_user() -> None:
    async with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        uid = u.id

    async with SessionLocal() as db:
        criadas = await seed_default_categories(db, uid)
        assert len(criadas) == len(DEFAULT_CATEGORIES) == 8
        for c in criadas:
            assert c.is_default is True
            assert c.color.startswith("#")
            assert c.icon
        await db.commit()

    async with SessionLocal() as db:
        all_cats = (
            (await db.execute(select(Category).where(Category.user_id == uid))).scalars().all()
        )
        assert len(all_cats) == 8


async def test_seed_e_idempotente() -> None:
    async with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        uid = u.id

    async with SessionLocal() as db:
        await seed_default_categories(db, uid)
        await db.commit()
    async with SessionLocal() as db:
        # segunda chamada nao adiciona
        novas = await seed_default_categories(db, uid)
        assert novas == []
    async with SessionLocal() as db:
        total = (await db.execute(select(Category).where(Category.user_id == uid))).scalars().all()
        assert len(total) == 8


async def test_register_dispara_seed_automatico() -> None:
    r = client.post(
        "/auth/register",
        json={"name": "Bia", "email": "bia@ex.com", "password": "senha123"},
    )
    assert r.status_code == 201
    uid = r.json()["id"]

    async with SessionLocal() as db:
        cats = (await db.execute(select(Category).where(Category.user_id == uid))).scalars().all()
        nomes = {c.name for c in cats}
        assert len(cats) == 8
        assert nomes == {n for (n, *_rest) in DEFAULT_CATEGORIES}
        assert all(c.is_default for c in cats)
