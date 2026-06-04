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


async def _seed_user_account_category() -> tuple[int, int, int]:
    async with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        await db.commit()
        acc = Account(
            user_id=u.id,
            name="N",
            type=AccountType.CHECKING,
            initial_balance=Decimal("0"),
            current_balance=Decimal("0"),
        )
        cat = Category(user_id=u.id, name="Lazer", type=CategoryType.EXPENSE)
        db.add_all([acc, cat])
        await db.commit()
        return u.id, acc.id, cat.id


async def test_transaction_basica() -> None:
    uid, aid, cid = await _seed_user_account_category()
    async with SessionLocal() as db:
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
        await db.commit()
        await db.refresh(t)
        assert t.id is not None
        assert t.is_recurring is False
        assert t.created_at is not None


async def test_transaction_user_id_invalido_quebra_fk() -> None:
    uid, aid, cid = await _seed_user_account_category()
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
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
            await db.commit()


async def test_transaction_account_id_invalido_quebra_fk() -> None:
    uid, _aid, cid = await _seed_user_account_category()
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
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
            await db.commit()


async def test_transaction_category_id_invalido_quebra_fk() -> None:
    uid, aid, _cid = await _seed_user_account_category()
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
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
            await db.commit()
