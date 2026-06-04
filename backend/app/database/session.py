"""Engine async e SessionLocal do SQLAlchemy + dependency get_db.

S01-T03 entregou a versao sincrona. S24-T01 migrou para SQLAlchemy async:
`get_db()` cede uma `AsyncSession` e todas as queries da app passam a usar
`await`. A normalizacao de URL permite que .env/CI continuem informando
drivers sincronos (ex.: `sqlite+pysqlite`, `postgresql+psycopg2`) sem
quebrar o `AsyncEngine` — o psycopg v3 ja suporta o modo async.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings

_settings = get_settings()


def _to_async_url(url: str) -> str:
    """Normaliza uma URL de banco para o driver async equivalente.

    Idempotente: URLs ja async (`sqlite+aiosqlite`, `postgresql+psycopg`)
    passam intactas.
    """
    if url.startswith("sqlite+pysqlite"):
        return url.replace("sqlite+pysqlite", "sqlite+aiosqlite", 1)
    if url.startswith("sqlite:"):
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    if url.startswith("postgresql+psycopg2"):
        return url.replace("postgresql+psycopg2", "postgresql+psycopg", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


_async_url = _to_async_url(_settings.database_url)

_engine_kwargs: dict = {"pool_pre_ping": True}
if _async_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _async_url:
        # sqlite:///:memory: cria um DB por conexao por padrao; StaticPool
        # garante que todas as sessions compartilhem a mesma conexao/dados.
        _engine_kwargs["poolclass"] = StaticPool
    else:
        # sqlite em arquivo (suite de testes async): NullPool abre uma conexao
        # nova por checkout, evitando reuso de conexao entre event loops
        # distintos (TestClient roda num portal loop proprio; testes diretos
        # rodam no loop do pytest-asyncio). Cada conexao nasce no loop corrente.
        _engine_kwargs["poolclass"] = NullPool

engine: AsyncEngine = create_async_engine(_async_url, **_engine_kwargs)


# sqlite nao impoe foreign keys por padrao; ligar pragma em cada conexao
# para que testes pegam violacoes de FK do mesmo jeito que Postgres pegaria.
# No engine async o listener vai no sync_engine subjacente.
if engine.dialect.name == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _conn_record) -> None:  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency e borda da Unit-of-Work (S24-T02).

    Cede uma AsyncSession; ao fim do request commita a transacao inteira
    (todas as operacoes do request num unico commit). Qualquer excecao no
    meio faz rollback total. Os services NAO commitam — apenas agrupam logica
    e usam flush() quando precisam de IDs/refresh dentro da transacao.
    """
    async with SessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
