"""Testes do model Account (S03-T01)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.accounts.models import Account, AccountType
from app.database.session import SessionLocal
from app.users.models import User


def _create_user(email: str = "ana@ex.com") -> User:
    with SessionLocal() as db:
        u = User(name="Ana", email=email, password_hash="h")
        db.add(u)
        db.commit()
        db.refresh(u)
        return u


def test_account_insercao_com_user_valido() -> None:
    user = _create_user()
    with SessionLocal() as db:
        acc = Account(
            user_id=user.id,
            name="Nubank",
            type=AccountType.CHECKING,
            initial_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )
        db.add(acc)
        db.commit()
        db.refresh(acc)
        assert acc.id is not None
        assert acc.is_active is True
        assert acc.created_at is not None
        assert acc.type == AccountType.CHECKING


def test_account_user_id_invalido_quebra_fk() -> None:
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Account(
                user_id=99999,
                name="Fantasma",
                type=AccountType.CASH,
                initial_balance=Decimal("0"),
                current_balance=Decimal("0"),
            )
        )
        db.commit()


def test_account_cascade_ao_deletar_user() -> None:
    user = _create_user()
    with SessionLocal() as db:
        db.add(
            Account(
                user_id=user.id,
                name="X",
                type=AccountType.CASH,
                initial_balance=Decimal("0"),
                current_balance=Decimal("0"),
            )
        )
        db.commit()

    # deletar usuario remove conta (ondelete CASCADE)
    with SessionLocal() as db:
        u = db.get(User, user.id)
        assert u is not None
        db.delete(u)
        db.commit()

    with SessionLocal() as db:
        from sqlalchemy import select

        contas = db.execute(select(Account).where(Account.user_id == user.id)).all()
        assert contas == []
