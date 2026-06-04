"""indices derivados de queries reais (S24-T04)

Revision ID: cfc7ddc4894e
Revises: 9a1c7e4b2f08
Create Date: 2026-06-03 17:47:12.340441

Indices derivados das queries reais do backend:

- budgets (user_id, month, year): a query BudgetRepository.list_for_user_month
  filtra exatamente por essas 3 colunas. Btree composto; criado em todos os
  dialetos.
- transactions (description) com gin_trgm_ops: a busca usa
  Transaction.description.ilike('%termo%') (curinga a esquerda), que so e
  acelerada por um indice trigram GIN. Especifico do PostgreSQL (exige a
  extensao pg_trgm); pulado no SQLite (suite de testes), onde a busca cai em
  table scan sem prejuizo funcional.

NOTA: o indice (user_id, date) em transactions ja existe desde a migration
inicial (ix_transactions_user_id_date) e por isso NAO e recriado aqui.

O indice GIN e gerenciado apenas por esta migration (nao esta no metadata dos
models, pois e Postgres-only); um eventual `alembic revision --autogenerate`
pode sugerir remove-lo — ignorar essa sugestao.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cfc7ddc4894e"
down_revision: Union[str, Sequence[str], None] = "9a1c7e4b2f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRGM_INDEX = "ix_transactions_description_trgm"
_BUDGETS_INDEX = "ix_budgets_user_id_month_year"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        _BUDGETS_INDEX,
        "budgets",
        ["user_id", "month", "year"],
        unique=False,
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.create_index(
            _TRGM_INDEX,
            "transactions",
            ["description"],
            unique=False,
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        )


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index(_TRGM_INDEX, table_name="transactions")
        # extensao pg_trgm nao e removida: pode estar em uso por outros objetos.

    op.drop_index(_BUDGETS_INDEX, table_name="budgets")
