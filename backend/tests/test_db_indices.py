"""Testes da migration de indices derivados de queries reais (S24-T04).

- Reversibilidade: a cadeia completa sobe ate head e desce ate base num SQLite
  limpo e isolado (subprocess com DATABASE_URL proprio), exercitando o
  `alembic upgrade/downgrade` exigido no criterio de aceitacao. O indice GIN
  (Postgres-only) e pulado no SQLite pela guarda de dialeto da migration.
- Sanity de uso de indice: EXPLAIN QUERY PLAN confirma que as queries-alvo
  (budgets por user_id/month/year e transactions por user_id/date) usam os
  indices compostos. O indice trigram de busca e Postgres-only e nao e
  exercitavel no SQLite (documentado).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.database.session import SessionLocal

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_migracao_reversivel_em_sqlite_limpo(tmp_path) -> None:
    """alembic upgrade head -> downgrade base num banco SQLite isolado."""
    db = tmp_path / "mig_reversibilidade.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db}",
        "JWT_SECRET": "test_secret",
        "ENVIRONMENT": "test",
    }

    up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert up.returncode == 0, f"upgrade falhou:\n{up.stdout}\n{up.stderr}"

    down = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert down.returncode == 0, f"downgrade falhou:\n{down.stdout}\n{down.stderr}"


async def _query_plan(sql: str) -> str:
    async with SessionLocal() as db:
        rows = (await db.execute(text("EXPLAIN QUERY PLAN " + sql))).all()
    return " | ".join(str(tuple(r)) for r in rows)


async def test_query_budgets_usa_indice_user_month_year() -> None:
    """A query real de budgets (filtro por user_id+month+year) usa o indice composto."""
    plan = await _query_plan(
        "SELECT * FROM budgets WHERE user_id = 1 AND month = 5 AND year = 2026"
    )
    assert "ix_budgets_user_id_month_year" in plan, plan


async def test_query_transactions_usa_indice_user_date() -> None:
    """A listagem de transacoes por usuario ordenada por data usa (user_id, date)."""
    plan = await _query_plan("SELECT * FROM transactions WHERE user_id = 1 ORDER BY date DESC")
    assert "ix_transactions_user_id_date" in plan, plan
