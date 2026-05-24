"""Testes do model Transaction (S05-T01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.accounts.models import Account, AccountType
from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.transactions.models import PaymentMethod, Transaction, TransactionType
from app.users.models import User


def _seed_user_account_category() -> tuple[int, int, int]:
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        acc = Account(
            user_id=u.id,
            name="N",
            type=AccountType.CHECKING,
            initial_balance=Decimal("0"),
            current_balance=Decimal("0"),
        )
        cat = Category(user_id=u.id, name="Lazer", type=CategoryType.EXPENSE)
        db.add_all([acc, cat])
        db.commit()
        return u.id, acc.id, cat.id


def test_transaction_basica() -> None:
    uid, aid, cid = _seed_user_account_category()
    with SessionLocal() as db:
        t = Transaction(
            user_id=uid,
            account_id=aid,
            category_id=cid,
            type=TransactionType.EXPENSE,
            amount=Decimal("12.50"),
            date=date(2026, 5, 23),
            description="Cafe",
            payment_method=PaymentMethod.CREDIT,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        assert t.id is not None
        assert t.is_recurring is False
        assert t.created_at is not None


def test_transaction_user_id_invalido_quebra_fk() -> None:
    uid, aid, cid = _seed_user_account_category()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Transaction(
                user_id=99999,
                account_id=aid,
                category_id=cid,
                type=TransactionType.EXPENSE,
                amount=Decimal("1"),
                date=date(2026, 5, 23),
            )
        )
        db.commit()


def test_transaction_account_id_invalido_quebra_fk() -> None:
    uid, _aid, cid = _seed_user_account_category()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Transaction(
                user_id=uid,
                account_id=99999,
                category_id=cid,
                type=TransactionType.EXPENSE,
                amount=Decimal("1"),
                date=date(2026, 5, 23),
            )
        )
        db.commit()


def test_transaction_category_id_invalido_quebra_fk() -> None:
    uid, aid, _cid = _seed_user_account_category()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Transaction(
                user_id=uid,
                account_id=aid,
                category_id=99999,
                type=TransactionType.INCOME,
                amount=Decimal("1"),
                date=date(2026, 5, 23),
            )
        )
        db.commit()
