"""Testes dos *Base schemas por entidade (S24-T03).

Garante o padrao DRY: para cada entidade existe um XxxBase com os campos
comuns de entrada, e Create/Read herdam dele. Inclui o round-trip
Read<->Base exigido: projetar um Read no subconjunto do Base e reconstruir
o Base produz um objeto equivalente, identico ao que Create (== Base) gera.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.accounts.schemas import AccountBase, AccountCreate, AccountRead
from app.budgets.schemas import (
    BudgetBase,
    BudgetCreate,
    BudgetRead,
    BudgetStatus,
    BudgetWithUsage,
)
from app.categories.schemas import CategoryBase, CategoryCreate, CategoryRead
from app.goals.schemas import GoalBase, GoalCreate, GoalRead
from app.transactions.schemas import TransactionBase, TransactionCreate, TransactionRead

_NOW = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)

# (Base, Create, Read, dados completos de um Read)
CASOS = [
    pytest.param(
        TransactionBase,
        TransactionCreate,
        TransactionRead,
        {
            "id": 1,
            "user_id": 9,
            "account_id": 2,
            "category_id": 3,
            "type": "expense",
            "amount": Decimal("12.34"),
            "date": date(2026, 5, 23),
            "description": "Mercado",
            "payment_method": "pix",
            "is_recurring": False,
            "created_at": _NOW,
        },
        id="transaction",
    ),
    pytest.param(
        AccountBase,
        AccountCreate,
        AccountRead,
        {
            "id": 1,
            "user_id": 9,
            "name": "Nubank",
            "type": "checking",
            "initial_balance": Decimal("100.00"),
            "current_balance": Decimal("150.00"),
            "is_active": True,
            "created_at": _NOW,
        },
        id="account",
    ),
    pytest.param(
        CategoryBase,
        CategoryCreate,
        CategoryRead,
        {
            "id": 1,
            "user_id": 9,
            "name": "Alimentacao",
            "type": "expense",
            "color": "#e74c3c",
            "icon": "utensils",
            "is_default": True,
        },
        id="category",
    ),
    pytest.param(
        BudgetBase,
        BudgetCreate,
        BudgetRead,
        {
            "id": 1,
            "user_id": 9,
            "category_id": 3,
            "month": 5,
            "year": 2026,
            "limit_amount": Decimal("500.00"),
        },
        id="budget",
    ),
    pytest.param(
        GoalBase,
        GoalCreate,
        GoalRead,
        {
            "id": 1,
            "user_id": 9,
            "name": "Reserva",
            "target_amount": Decimal("1000.00"),
            "current_amount": Decimal("250.00"),
            "deadline": date(2026, 12, 31),
            "status": "in_progress",
        },
        id="goal",
    ),
]


@pytest.mark.parametrize(("base_cls", "create_cls", "read_cls", "read_data"), CASOS)
def test_create_e_read_herdam_de_base(base_cls, create_cls, read_cls, read_data) -> None:
    assert issubclass(create_cls, base_cls)
    assert issubclass(read_cls, base_cls)


@pytest.mark.parametrize(("base_cls", "create_cls", "read_cls", "read_data"), CASOS)
def test_base_sem_campos_de_resposta(base_cls, create_cls, read_cls, read_data) -> None:
    """O Base nao deve conter campos exclusivos de resposta (id/user_id/created_at)."""
    base_fields = set(base_cls.model_fields)
    assert "id" not in base_fields
    assert "user_id" not in base_fields
    assert "created_at" not in base_fields


@pytest.mark.parametrize(("base_cls", "create_cls", "read_cls", "read_data"), CASOS)
def test_read_base_roundtrip(base_cls, create_cls, read_cls, read_data) -> None:
    """Round-trip Read<->Base: projetar o Read no subconjunto do Base e
    reconstruir o Base produz o mesmo dump que Create (== Base) com os
    mesmos dados. Garante que Read carrega fielmente os campos do Base."""
    read = read_cls(**read_data)

    base_fields = list(base_cls.model_fields)
    # todos os campos do Base existem no Read (heranca efetiva)
    assert set(base_fields).issubset(set(read_cls.model_fields))

    projecao = {k: getattr(read, k) for k in base_fields}
    base = base_cls(**projecao)
    create = create_cls(**projecao)

    # Base <-> Read coincidem no subconjunto comum; Create (== Base) idem
    assert base.model_dump() == create.model_dump()
    assert base.model_dump() == {k: getattr(read, k) for k in base_fields}


def test_budget_with_usage_herda_read_e_acrescenta_uso() -> None:
    """BudgetWithUsage estende BudgetRead apenas com os campos de uso."""
    assert issubclass(BudgetWithUsage, BudgetRead)
    extras = set(BudgetWithUsage.model_fields) - set(BudgetRead.model_fields)
    assert extras == {"used_amount", "percent_used", "status"}

    bwu = BudgetWithUsage(
        id=1,
        user_id=9,
        category_id=3,
        month=5,
        year=2026,
        limit_amount=Decimal("500.00"),
        used_amount=Decimal("200.00"),
        percent_used=Decimal("40.00"),
        status=BudgetStatus.OK,
    )
    # campos herdados do BudgetRead/Base preservados
    assert bwu.limit_amount == Decimal("500.00")
    assert bwu.status is BudgetStatus.OK
