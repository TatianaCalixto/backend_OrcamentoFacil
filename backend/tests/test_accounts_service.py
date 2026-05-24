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
def user_a() -> int:
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        return u.id


@pytest.fixture
def user_b() -> int:
    with SessionLocal() as db:
        u = User(name="B", email="b@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        return u.id


def test_service_create_inicializa_current_balance_igual_initial(user_a: int) -> None:
    with SessionLocal() as db:
        svc = AccountService(db)
        acc = svc.create_for_user(
            user_a,
            AccountCreate(name="N", type=AccountType.CHECKING, initial_balance=Decimal("250.00")),
        )
        assert acc.current_balance == Decimal("250.00")
        assert acc.initial_balance == Decimal("250.00")
        assert acc.user_id == user_a
        assert acc.is_active is True


def test_service_list_isola_por_usuario(user_a: int, user_b: int) -> None:
    with SessionLocal() as db:
        svc = AccountService(db)
        svc.create_for_user(user_a, AccountCreate(name="A1", type=AccountType.CASH))
        svc.create_for_user(user_a, AccountCreate(name="A2", type=AccountType.CASH))
        svc.create_for_user(user_b, AccountCreate(name="B1", type=AccountType.CASH))

    with SessionLocal() as db:
        svc = AccountService(db)
        as_a = svc.list_for_user(user_a)
        as_b = svc.list_for_user(user_b)
        assert {a.name for a in as_a} == {"A1", "A2"}
        assert {a.name for a in as_b} == {"B1"}


def test_service_get_nao_expoe_conta_de_outro_usuario(user_a: int, user_b: int) -> None:
    with SessionLocal() as db:
        acc = AccountService(db).create_for_user(
            user_a, AccountCreate(name="A1", type=AccountType.CASH)
        )

    with SessionLocal() as db:
        svc = AccountService(db)
        assert svc.get_for_user(user_a, acc.id) is not None
        assert svc.get_for_user(user_b, acc.id) is None


def test_service_update_aplica_patch_parcial(user_a: int) -> None:
    with SessionLocal() as db:
        acc = AccountService(db).create_for_user(
            user_a, AccountCreate(name="Old", type=AccountType.CASH)
        )

    with SessionLocal() as db:
        svc = AccountService(db)
        upd = svc.update_for_user(user_a, acc.id, AccountUpdate(name="New", is_active=False))
        assert upd is not None
        assert upd.name == "New"
        assert upd.is_active is False
        assert upd.type == AccountType.CASH  # nao tocado


def test_service_update_para_conta_de_outro_usuario_retorna_none(user_a: int, user_b: int) -> None:
    with SessionLocal() as db:
        acc = AccountService(db).create_for_user(
            user_a, AccountCreate(name="X", type=AccountType.CASH)
        )

    with SessionLocal() as db:
        upd = AccountService(db).update_for_user(user_b, acc.id, AccountUpdate(name="hack"))
        assert upd is None


def test_service_delete_isolado_por_usuario(user_a: int, user_b: int) -> None:
    with SessionLocal() as db:
        acc = AccountService(db).create_for_user(
            user_a, AccountCreate(name="X", type=AccountType.CASH)
        )

    with SessionLocal() as db:
        assert AccountService(db).delete_for_user(user_b, acc.id) is False
    with SessionLocal() as db:
        assert AccountService(db).get_for_user(user_a, acc.id) is not None
    with SessionLocal() as db:
        assert AccountService(db).delete_for_user(user_a, acc.id) is True
    with SessionLocal() as db:
        assert AccountService(db).get_for_user(user_a, acc.id) is None
