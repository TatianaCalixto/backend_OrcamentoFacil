"""Testes do model Goal (S07-T01)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.goals.models import Goal, GoalStatus
from app.users.models import User


def _make_user() -> int:
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        return u.id


def test_goal_basico() -> None:
    uid = _make_user()
    with SessionLocal() as db:
        g = Goal(user_id=uid, name="Reserva", target_amount=Decimal("1000.00"))
        db.add(g)
        db.commit()
        db.refresh(g)
        assert g.id is not None
        assert g.status == GoalStatus.IN_PROGRESS
        assert g.current_amount == Decimal("0.00")


def test_goal_target_amount_zero_falha() -> None:
    uid = _make_user()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(Goal(user_id=uid, name="X", target_amount=Decimal("0")))
        db.commit()


def test_goal_current_amount_negativo_falha() -> None:
    uid = _make_user()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            Goal(user_id=uid, name="X", target_amount=Decimal("100"), current_amount=Decimal("-1"))
        )
        db.commit()
