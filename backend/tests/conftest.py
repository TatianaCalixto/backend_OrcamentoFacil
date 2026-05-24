"""Fixtures e configuracao global do pytest.

Define os ENV minimos exigidos pelo Settings (S01-T02) ANTES que
qualquer modulo da app seja importado. Se o ambiente ja tiver
DATABASE_URL/JWT_SECRET definidos (caso do CI), os valores ja
existentes sao respeitados (setdefault).
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test_secret_change_me")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402

# Import dos modelos para registrar em Base.metadata.
# Cada novo modulo de modelo deve ser adicionado aqui.
from app.accounts import models as _accounts_models  # noqa: E402, F401
from app.categories import models as _categories_models  # noqa: E402, F401
from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.transactions import models as _transactions_models  # noqa: E402, F401
from app.users import models as _users_models  # noqa: E402, F401


@pytest.fixture(autouse=True)
def _setup_schema():
    """Recria o schema antes de cada teste (isolamento)."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
