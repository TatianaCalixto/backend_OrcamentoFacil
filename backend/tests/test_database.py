"""Testes da camada de banco: engine/session/get_db (S01-T03; async em S24-T01)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import SessionLocal, get_db


async def test_session_executa_select_1() -> None:
    async with SessionLocal() as db:
        result = (await db.execute(text("SELECT 1"))).scalar_one()
    assert result == 1


async def test_get_db_cede_session_que_executa_select_1() -> None:
    gen = get_db()
    db = await gen.__anext__()
    try:
        assert isinstance(db, AsyncSession)
        assert (await db.execute(text("SELECT 1"))).scalar_one() == 1
    finally:
        # esgota o async generator (executa o finally interno -> close via async with)
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()


class _FakeAsyncCM:
    """Context manager async falso, no formato que `async with SessionLocal()`
    espera: __aenter__ cede a session; __aexit__ delega a um mock awaitable."""

    def __init__(self, session, aexit) -> None:
        self._session = session
        self._aexit = aexit

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return await self._aexit(*args)


async def test_get_db_faz_rollback_em_erro(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando uma excecao ocorre dentro do bloco que usa a session,
    get_db deve chamar rollback antes de propagar."""
    fake_session = MagicMock(spec=AsyncSession)
    fake_session.rollback = AsyncMock()
    cm = _FakeAsyncCM(fake_session, AsyncMock(return_value=False))

    monkeypatch.setattr("app.database.session.SessionLocal", lambda: cm)
    from app.database import session as session_mod

    gen = session_mod.get_db()
    yielded = await gen.__anext__()
    assert yielded is fake_session

    with pytest.raises(RuntimeError, match="boom"):
        await gen.athrow(RuntimeError("boom"))

    fake_session.rollback.assert_awaited_once()


async def test_get_db_fecha_session_no_caminho_feliz(monkeypatch: pytest.MonkeyPatch) -> None:
    """No caminho feliz, get_db deve sair do context manager (close via __aexit__)
    sem chamar rollback."""
    fake_session = MagicMock(spec=AsyncSession)
    fake_session.rollback = AsyncMock()
    aexit = AsyncMock(return_value=False)
    cm = _FakeAsyncCM(fake_session, aexit)

    monkeypatch.setattr("app.database.session.SessionLocal", lambda: cm)
    from app.database import session as session_mod

    gen = session_mod.get_db()
    await gen.__anext__()
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    aexit.assert_awaited_once()
    fake_session.rollback.assert_not_called()
