"""Testes do BudgetService — calculo de uso e alertas (S06-T02)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.accounts.models import Account, AccountType
from app.budgets.models import Budget
from app.budgets.schemas import BudgetCreate, BudgetStatus
from app.budgets.service import BudgetOwnershipError, BudgetService
from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.transactions.models import Transaction, TransactionType
from app.users.models import User


@pytest.fixture
def setup_a():
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        acc = Account(
            user_id=u.id,
            name="C",
            type=AccountType.CHECKING,
            initial_balance=Decimal("1000"),
            current_balance=Decimal("1000"),
        )
        cat = Category(user_id=u.id, name="Mercado", type=CategoryType.EXPENSE)
        cat_in = Category(user_id=u.id, name="Salario", type=CategoryType.INCOME)
        db.add_all([acc, cat, cat_in])
        db.commit()
        # budget de 500 em maio/2026
        b = Budget(
            user_id=u.id,
            category_id=cat.id,
            month=5,
            year=2026,
            limit_amount=Decimal("500.00"),
        )
        db.add(b)
        db.commit()
        return {"uid": u.id, "acc": acc.id, "cat": cat.id, "cat_in": cat_in.id, "budget_id": b.id}


def _add_txn(uid: int, acc: int, cat: int, type_: TransactionType, amount: str, dt: date) -> None:
    with SessionLocal() as db:
        db.add(
            Transaction(
                user_id=uid,
                account_id=acc,
                category_id=cat,
                type=type_,
                amount=Decimal(amount),
                date=dt,
            )
        )
        db.commit()


def _usage(uid: int, bid: int):
    with SessionLocal() as db:
        return BudgetService(db).get_with_usage(uid, bid)


# --------------------- testes da regra ---------------------


def test_sem_transacoes_retorna_zero_e_ok(setup_a) -> None:
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.used_amount == Decimal("0")
    assert u.percent_used == Decimal("0.00")
    assert u.status == BudgetStatus.OK


def test_metade_do_limite_retorna_50_e_ok(setup_a) -> None:
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "250.00",
        date(2026, 5, 10),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.used_amount == Decimal("250.00")
    assert u.percent_used == Decimal("50.00")
    assert u.status == BudgetStatus.OK


def test_85_porcento_retorna_warning(setup_a) -> None:
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "425.00",
        date(2026, 5, 15),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.percent_used == Decimal("85.00")
    assert u.status == BudgetStatus.WARNING


def test_120_porcento_retorna_critical(setup_a) -> None:
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "600.00",
        date(2026, 5, 20),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.percent_used == Decimal("120.00")
    assert u.status == BudgetStatus.CRITICAL


def test_exatos_80_eh_ok_e_acima_de_80_eh_warning(setup_a) -> None:
    # 80% -> ok (regra: warning eh >80%)
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "400.00",
        date(2026, 5, 5),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.percent_used == Decimal("80.00")
    assert u.status == BudgetStatus.OK

    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "5.00",
        date(2026, 5, 6),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.percent_used == Decimal("81.00")
    assert u.status == BudgetStatus.WARNING


def test_exatos_100_eh_warning_e_acima_eh_critical(setup_a) -> None:
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "500.00",
        date(2026, 5, 1),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.percent_used == Decimal("100.00")
    assert u.status == BudgetStatus.WARNING

    # passa de 100 -> critical (sobe para 101%)
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "5.00",
        date(2026, 5, 2),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.status == BudgetStatus.CRITICAL


def test_transacao_de_mes_adjacente_nao_conta(setup_a) -> None:
    # 30 abril e 1 junho NAO contam para o budget de maio
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "100",
        date(2026, 4, 30),
    )
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.EXPENSE,
        "100",
        date(2026, 6, 1),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.used_amount == Decimal("0")


def test_transacao_de_categoria_diferente_nao_conta(setup_a) -> None:
    # cria outra categoria expense, valor alto, mas budget e' so para "cat"
    with SessionLocal() as db:
        outra = Category(user_id=setup_a["uid"], name="Outra", type=CategoryType.EXPENSE)
        db.add(outra)
        db.commit()
        outra_id = outra.id
    _add_txn(
        setup_a["uid"], setup_a["acc"], outra_id, TransactionType.EXPENSE, "999", date(2026, 5, 15)
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.used_amount == Decimal("0")


def test_transacao_de_receita_nao_conta(setup_a) -> None:
    # uma receita NA MESMA categoria (estranho, mas valido) nao conta como uso
    _add_txn(
        setup_a["uid"],
        setup_a["acc"],
        setup_a["cat"],
        TransactionType.INCOME,
        "999",
        date(2026, 5, 15),
    )
    u = _usage(setup_a["uid"], setup_a["budget_id"])
    assert u.used_amount == Decimal("0")
    assert u.status == BudgetStatus.OK


def test_create_for_user_rejeita_category_de_outro_user(setup_a) -> None:
    with SessionLocal() as db:
        outro = User(name="B", email="b@ex.com", password_hash="h")
        db.add(outro)
        db.commit()
        cat_out = Category(user_id=outro.id, name="X", type=CategoryType.EXPENSE)
        db.add(cat_out)
        db.commit()
        cat_out_id = cat_out.id

    with SessionLocal() as db, pytest.raises(BudgetOwnershipError):
        BudgetService(db).create_for_user(
            setup_a["uid"],
            BudgetCreate(
                category_id=cat_out_id,
                month=5,
                year=2026,
                limit_amount=Decimal("100"),
            ),
        )
