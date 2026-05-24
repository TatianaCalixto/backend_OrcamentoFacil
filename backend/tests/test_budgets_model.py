"""Testes do model Budget (S06-T01)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.budgets.models import Budget
from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.users.models import User


def _seed_user_category() -> tuple[int, int]:
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        c = Category(user_id=u.id, name="Lazer", type=CategoryType.EXPENSE)
        db.add(c)
        db.commit()
        return u.id, c.id


def test_budget_basico() -> None:
    uid, cid = _seed_user_category()
    with SessionLocal() as db:
        b = Budget(
            user_id=uid,
            category_id=cid,
            month=5,
            year=2026,
            limit_amount=Decimal("500.00"),
        )
        db.add(b)
        db.commit()
        db.refresh(b)
        assert b.id is not None


def test_budget_duplicado_quebra_unique() -> None:
    uid, cid = _seed_user_category()
    with SessionLocal() as db:
        db.add(
            Budget(user_id=uid, category_id=cid, month=5, year=2026, limit_amount=Decimal("500"))
        )
        db.commit()

    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Budget(user_id=uid, category_id=cid, month=5, year=2026, limit_amount=Decimal("800"))
        )
        db.commit()


def test_budget_mesmo_user_e_cat_em_meses_distintos_ok() -> None:
    uid, cid = _seed_user_category()
    with SessionLocal() as db:
        db.add_all(
            [
                Budget(
                    user_id=uid, category_id=cid, month=5, year=2026, limit_amount=Decimal("100")
                ),
                Budget(
                    user_id=uid, category_id=cid, month=6, year=2026, limit_amount=Decimal("200")
                ),
                Budget(
                    user_id=uid, category_id=cid, month=5, year=2027, limit_amount=Decimal("300")
                ),
            ]
        )
        db.commit()  # nao quebra


def test_budget_check_constraints() -> None:
    uid, cid = _seed_user_category()
    # month invalido
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(Budget(user_id=uid, category_id=cid, month=13, year=2026, limit_amount=Decimal("1")))
        db.commit()


def test_budget_limit_amount_zero_falha() -> None:
    uid, cid = _seed_user_category()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(Budget(user_id=uid, category_id=cid, month=5, year=2026, limit_amount=Decimal("0")))
        db.commit()
