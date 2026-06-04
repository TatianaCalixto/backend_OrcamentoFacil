"""Testes da Unit-of-Work na borda do request (S24-T02).

A partir da S24-T02 os services NAO commitam: quem commita/rollback e a
dependency `get_db` no fim do request. Estes testes dirigem o async generator
`get_db()` do mesmo jeito que o FastAPI dirige (anext -> commit no sucesso;
athrow -> rollback no erro) e provam:

- caminho feliz: 2 operacoes no mesmo request -> UM commit -> ambas persistem;
- erro na 2a operacao -> rollback TOTAL -> saldo inalterado (a 1a operacao,
  ja flushada, tambem e revertida).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.accounts.models import Account, AccountType
from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal, get_db
from app.transactions.models import TransactionType
from app.transactions.schemas import TransactionCreate
from app.transactions.service import OwnershipError, TransactionService
from app.users.models import User

INICIAL = Decimal("1000.00")


@pytest.fixture
async def uow_setup() -> dict:
    """Usuario A com 1 conta (saldo inicial 1000) e 1 categoria de receita;
    mais a conta de OUTRO usuario (para forcar OwnershipError na 2a operacao)."""
    async with SessionLocal() as db:
        a = User(name="A", email="uow_a@ex.com", password_hash="h")
        b = User(name="B", email="uow_b@ex.com", password_hash="h")
        db.add_all([a, b])
        await db.commit()
        acc = Account(
            user_id=a.id,
            name="Conta A",
            type=AccountType.CHECKING,
            initial_balance=INICIAL,
            current_balance=INICIAL,
        )
        cat = Category(user_id=a.id, name="Salario", type=CategoryType.INCOME)
        acc_b = Account(
            user_id=b.id,
            name="Conta B",
            type=AccountType.CHECKING,
            initial_balance=Decimal("0.00"),
            current_balance=Decimal("0.00"),
        )
        db.add_all([acc, cat, acc_b])
        await db.commit()
        return {
            "user_id": a.id,
            "acc_id": acc.id,
            "cat_id": cat.id,
            "acc_alheia_id": acc_b.id,
        }


async def _saldo(account_id: int) -> Decimal:
    async with SessionLocal() as db:
        acc = await db.get(Account, account_id)
        assert acc is not None
        return acc.current_balance


def _income(account_id: int, category_id: int, amount: str) -> TransactionCreate:
    return TransactionCreate(
        account_id=account_id,
        category_id=category_id,
        type=TransactionType.INCOME,
        amount=Decimal(amount),
        date=date(2026, 5, 23),
    )


async def test_uow_commit_persiste_ambas_operacoes(uow_setup) -> None:
    """Caminho feliz: 2 creates no MESMO request -> borda commita -> ambas valem."""
    gen = get_db()
    db = await gen.__anext__()
    svc = TransactionService(db)
    await svc.create_for_user(
        uow_setup["user_id"], _income(uow_setup["acc_id"], uow_setup["cat_id"], "100.00")
    )
    await svc.create_for_user(
        uow_setup["user_id"], _income(uow_setup["acc_id"], uow_setup["cat_id"], "50.00")
    )
    # esgotar o generator dispara o commit da borda (get_db)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

    assert await _saldo(uow_setup["acc_id"]) == Decimal("1150.00")  # 1000 + 100 + 50


async def test_uow_rollback_total_quando_segunda_operacao_falha(uow_setup) -> None:
    """Erro na 2a operacao -> rollback TOTAL. A 1a operacao (ja flushada) NAO
    persiste: saldo permanece no inicial."""
    gen = get_db()
    db = await gen.__anext__()
    svc = TransactionService(db)

    # op1 OK: cria receita de 100 (flush dentro da transacao, sem commit)
    await svc.create_for_user(
        uow_setup["user_id"], _income(uow_setup["acc_id"], uow_setup["cat_id"], "100.00")
    )

    # op2 falha: conta de outro usuario -> OwnershipError
    with pytest.raises(OwnershipError):
        await svc.create_for_user(
            uow_setup["user_id"], _income(uow_setup["acc_alheia_id"], uow_setup["cat_id"], "50.00")
        )

    # a borda (get_db) recebe a excecao do request e faz rollback total
    with pytest.raises(OwnershipError):
        await gen.athrow(OwnershipError("falha simulada na 2a operacao do request"))

    # saldo inalterado: a op1 tambem foi revertida (UoW)
    assert await _saldo(uow_setup["acc_id"]) == INICIAL
