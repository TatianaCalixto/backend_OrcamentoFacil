"""Engine e SessionLocal do SQLAlchemy + dependency get_db (S01-T03)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_settings = get_settings()

_engine_kwargs: dict = {"future": True, "pool_pre_ping": True}
if _settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    # sqlite:///:memory: cria um DB por conexao por padrao; StaticPool
    # garante que todas as sessions compartilhem a mesma conexao/dados.
    if ":memory:" in _settings.database_url:
        _engine_kwargs["poolclass"] = StaticPool

engine: Engine = create_engine(_settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: cede uma Session e garante rollback/close."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
