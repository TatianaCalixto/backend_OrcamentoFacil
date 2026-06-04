"""Testes do AccountService + AccountRepository (S03-T03)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.accounts.models import AccountType
from app.accounts.schemas import AccountCreate, AccountUpdate
from app.accounts.service import AccountService
from app.database.session import SessionLocal
from app.users.models import User


@pytest.fixture
async def user_a() -> int:
    async with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        return u.id


@pytest.fixture
async def user_b() -> int:
    async with SessionLocal() as db:
        u = User(name="B", email="b@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        return u.id


async def test_service_create_inicializa_current_balance_igual_initial(user_a: int) -> None:
    async with SessionLocal() as db:
        svc = AccountService(db)
        acc = await svc.create_for_user(
            user_a,
            AccountCreate(name="N", type=AccountType.CHECKING, initial_balance=Decimal("250.00")),
        )
        assert acc.current_balance == Decimal("250.00")
        assert acc.initial_balance == Decimal("250.00")
        assert acc.user_id == user_a
        assert acc.is_active is True
        await db.commit()


async def test_service_list_isola_por_usuario(user_a: int, user_b: int) -> None:
    async with SessionLocal() as db:
        svc = AccountService(db)
        await svc.create_for_user(user_a, AccountCreate(name="A1", type=AccountType.CASH))
        await svc.create_for_user(user_a, AccountCreate(name="A2", type=AccountType.CASH))
        await svc.create_for_user(user_b, AccountCreate(name="B1", type=AccountType.CASH))
        await db.commit()

    async with SessionLocal() as db:
        svc = AccountService(db)
        as_a = await svc.list_for_user(user_a)
        as_b = await svc.list_for_user(user_b)
        assert {a.name for a in as_a} == {"A1", "A2"}
        assert {a.name for a in as_b} == {"B1"}


async def test_service_get_nao_expoe_conta_de_outro_usuario(user_a: int, user_b: int) -> None:
    async with SessionLocal() as db:
        acc = await AccountService(db).create_for_user(
            user_a, AccountCreate(name="A1", type=AccountType.CASH)
        )
        await db.commit()

    async with SessionLocal() as db:
        svc = AccountService(db)
        assert await svc.get_for_user(user_a, acc.id) is not None
        assert await svc.get_for_user(user_b, acc.id) is None


async def test_service_update_aplica_patch_parcial(user_a: int) -> None:
    async with SessionLocal() as db:
        acc = await AccountService(db).create_for_user(
            user_a, AccountCreate(name="Old", type=AccountType.CASH)
        )
        await db.commit()

    async with SessionLocal() as db:
        svc = AccountService(db)
        upd = await svc.update_for_user(user_a, acc.id, AccountUpdate(name="New", is_active=False))
        assert upd is not None
        assert upd.name == "New"
        assert upd.is_active is False
        assert upd.type == AccountType.CASH  # nao tocado
        await db.commit()


async def test_service_update_para_conta_de_outro_usuario_retorna_none(
    user_a: int, user_b: int
) -> None:
    async with SessionLocal() as db:
        acc = await AccountService(db).create_for_user(
            user_a, AccountCreate(name="X", type=AccountType.CASH)
        )
        await db.commit()

    async with SessionLocal() as db:
        upd = await AccountService(db).update_for_user(user_b, acc.id, AccountUpdate(name="hack"))
        assert upd is None


async def test_service_delete_isolado_por_usuario(user_a: int, user_b: int) -> None:
    async with SessionLocal() as db:
        acc = await AccountService(db).create_for_user(
            user_a, AccountCreate(name="X", type=AccountType.CASH)
        )
        await db.commit()

    async with SessionLocal() as db:
        assert await AccountService(db).delete_for_user(user_b, acc.id) is False
    async with SessionLocal() as db:
        assert await AccountService(db).get_for_user(user_a, acc.id) is not None
    async with SessionLocal() as db:
        assert await AccountService(db).delete_for_user(user_a, acc.id) is True
        await db.commit()
    async with SessionLocal() as db:
        assert await AccountService(db).get_for_user(user_a, acc.id) is None
