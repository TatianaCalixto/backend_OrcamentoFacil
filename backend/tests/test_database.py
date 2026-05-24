"""Testes da camada de banco: engine/session/get_db (S01-T03)."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db


def test_session_executa_select_1() -> None:
    with SessionLocal() as db:
        result = db.execute(text("SELECT 1")).scalar_one()
    assert result == 1


def test_get_db_cede_session_que_executa_select_1() -> None:
    gen: Generator[Session, None, None] = get_db()
    db = next(gen)
    try:
        assert isinstance(db, Session)
        assert db.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        # encerra o generator (executa o finally interno -> close)
        with pytest.raises(StopIteration):
            next(gen)


def test_get_db_faz_rollback_em_erro(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando uma excecao ocorre dentro do bloco que usa a session,
    get_db deve chamar rollback antes de propagar."""
    fake_session = MagicMock(spec=Session)

    def fake_session_factory() -> MagicMock:
        return fake_session

    monkeypatch.setattr("app.database.session.SessionLocal", fake_session_factory)
    # reimporta get_db apos o patch para resolver SessionLocal localmente:
    from app.database import session as session_mod

    gen = session_mod.get_db()
    yielded = next(gen)
    assert yielded is fake_session

    with pytest.raises(RuntimeError, match="boom"):
        gen.throw(RuntimeError("boom"))

    fake_session.rollback.assert_called_once()
    fake_session.close.assert_called_once()


def test_get_db_fecha_session_no_caminho_feliz(monkeypatch: pytest.MonkeyPatch) -> None:
    """No caminho feliz, get_db deve fechar a session (sem rollback)."""
    fake_session = MagicMock(spec=Session)

    monkeypatch.setattr("app.database.session.SessionLocal", lambda: fake_session)
    from app.database import session as session_mod

    gen = session_mod.get_db()
    next(gen)
    with pytest.raises(StopIteration):
        next(gen)

    fake_session.close.assert_called_once()
    fake_session.rollback.assert_not_called()
