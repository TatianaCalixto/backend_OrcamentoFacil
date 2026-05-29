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
from app.auth import models as _auth_models  # noqa: E402, F401
from app.budgets import models as _budgets_models  # noqa: E402, F401
from app.categories import models as _categories_models  # noqa: E402, F401
from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.goals import models as _goals_models  # noqa: E402, F401
from app.transactions import models as _transactions_models  # noqa: E402, F401
from app.users import models as _users_models  # noqa: E402, F401


@pytest.fixture(autouse=True)
def _setup_schema():
    """Recria o schema antes de cada teste (isolamento)."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Desabilita o rate limit por padrao nos testes e limpa o storage entre
    eles. A partir da S20-T03 ha limites nas mutacoes (transactions/accounts/
    budgets/goals/imports); sem desabilitar por padrao, testes que criam varios
    recursos (ex.: regressao de saldo) estourariam 429. Testes que querem
    validar 429 reabilitam via a fixture rate_limit_active."""
    from app.core.ratelimit import limiter

    limiter.enabled = False
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def rate_limit_active():
    """Reabilita o limiter para o teste atual (opt-in). Roda apos o autouse
    _reset_rate_limit, entao prevalece (enabled=True)."""
    from app.core.ratelimit import limiter

    limiter.enabled = True
    yield
    limiter.enabled = False
