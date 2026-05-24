"""Testes do model User (S02-T01)."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.session import SessionLocal
from app.users.models import User


def test_insercao_de_user_persiste_campos() -> None:
    with SessionLocal() as db:
        u = User(name="Ana", email="ana@ex.com", password_hash="hash")
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.id is not None
        assert u.created_at is not None
        assert u.email == "ana@ex.com"


def test_email_duplicado_quebra_unique() -> None:
    with SessionLocal() as db:
        db.add(User(name="A", email="dup@ex.com", password_hash="h"))
        db.commit()

    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(User(name="B", email="dup@ex.com", password_hash="h2"))
        db.commit()


def test_email_unico_case_sensitive_default() -> None:
    """Por padrao, sqlite distingue caixa; teste documenta o comportamento atual.
    Normalizacao de email (lowercasing) e regra de negocio que vira em S02-T04."""
    with SessionLocal() as db:
        db.add(User(name="A", email="caps@ex.com", password_hash="h"))
        db.commit()
    with SessionLocal() as db:
        # email com caixa diferente NAO bate o unique no sqlite default
        db.add(User(name="B", email="CAPS@ex.com", password_hash="h2"))
        db.commit()
