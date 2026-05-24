"""Testes do TransactionService — REGRA CRITICA DE SALDO (S05-T03).

Estes testes formam a primeira camada de regressao de saldo. A bateria
end-to-end vem em test_balance_regression.py (S05-T05).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.accounts.models import Account, AccountType
from app.categories.models import Category, CategoryType
from app.database.session import SessionLocal
from app.transactions.models import TransactionType
from app.transactions.schemas import TransactionCreate, TransactionUpdate
from app.transactions.service import OwnershipError, TransactionService
from app.users.models import User

# --------------------------- fixtures ---------------------------


@pytest.fixture
def setup_a():
    """Cria user A com 2 contas e 2 categorias."""
    with SessionLocal() as db:
        u = User(name="A", email="a@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        acc1 = Account(
            user_id=u.id,
            name="C1",
            type=AccountType.CHECKING,
            initial_balance=Decimal("100.00"),
            current_balance=Decimal("100.00"),
        )
        acc2 = Account(
            user_id=u.id,
            name="C2",
            type=AccountType.SAVINGS,
            initial_balance=Decimal("0.00"),
            current_balance=Decimal("0.00"),
        )
        cat_in = Category(user_id=u.id, name="Salario", type=CategoryType.INCOME)
        cat_ex = Category(user_id=u.id, name="Mercado", type=CategoryType.EXPENSE)
        db.add_all([acc1, acc2, cat_in, cat_ex])
        db.commit()
        return {
            "user_id": u.id,
            "acc1_id": acc1.id,
            "acc2_id": acc2.id,
            "cat_in_id": cat_in.id,
            "cat_ex_id": cat_ex.id,
        }


@pytest.fixture
def user_b_ids():
    """User B com 1 conta e 1 categoria (para testes de ownership cruzado)."""
    with SessionLocal() as db:
        u = User(name="B", email="b@ex.com", password_hash="h")
        db.add(u)
        db.commit()
        acc = Account(
            user_id=u.id,
            name="BC1",
            type=AccountType.CASH,
            initial_balance=Decimal("0"),
            current_balance=Decimal("0"),
        )
        cat = Category(user_id=u.id, name="BCat", type=CategoryType.EXPENSE)
        db.add_all([acc, cat])
        db.commit()
        return {"user_id": u.id, "acc_id": acc.id, "cat_id": cat.id}


def _balance(account_id: int) -> Decimal:
    with SessionLocal() as db:
        acc = db.get(Account, account_id)
        assert acc is not None
        return acc.current_balance


# --------------------------- create ---------------------------


def test_create_receita_aumenta_saldo(setup_a) -> None:
    with SessionLocal() as db:
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("50.00"),
                date=date(2026, 5, 23),
            ),
        )
    assert _balance(setup_a["acc1_id"]) == Decimal("150.00")  # 100 + 50


def test_create_despesa_diminui_saldo(setup_a) -> None:
    with SessionLocal() as db:
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_ex_id"],
                type=TransactionType.EXPENSE,
                amount=Decimal("30.00"),
                date=date(2026, 5, 23),
            ),
        )
    assert _balance(setup_a["acc1_id"]) == Decimal("70.00")  # 100 - 30


def test_create_account_de_outro_user_rejeita(setup_a, user_b_ids) -> None:
    with SessionLocal() as db, pytest.raises(OwnershipError):
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=user_b_ids["acc_id"],  # NAO eh do user A
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("10"),
                date=date(2026, 5, 23),
            ),
        )


def test_create_category_de_outro_user_rejeita(setup_a, user_b_ids) -> None:
    with SessionLocal() as db, pytest.raises(OwnershipError):
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=user_b_ids["cat_id"],  # NAO eh do user A
                type=TransactionType.INCOME,
                amount=Decimal("10"),
                date=date(2026, 5, 23),
            ),
        )


# --------------------------- update ---------------------------


def test_update_amount_ajusta_delta(setup_a) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_ex_id"],
                type=TransactionType.EXPENSE,
                amount=Decimal("10.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    # 100 - 10 = 90
    assert _balance(setup_a["acc1_id"]) == Decimal("90.00")

    with SessionLocal() as db:
        TransactionService(db).update_for_user(
            setup_a["user_id"], tid, TransactionUpdate(amount=Decimal("25.00"))
        )
    # delta = -25 - (-10) = -15; 90 + (-15) = 75
    assert _balance(setup_a["acc1_id"]) == Decimal("75.00")


def test_update_muda_tipo_de_receita_para_despesa(setup_a) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("40.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    # 100 + 40 = 140
    assert _balance(setup_a["acc1_id"]) == Decimal("140.00")

    with SessionLocal() as db:
        TransactionService(db).update_for_user(
            setup_a["user_id"], tid, TransactionUpdate(type=TransactionType.EXPENSE)
        )
    # delta = -40 - (+40) = -80; 140 + (-80) = 60
    assert _balance(setup_a["acc1_id"]) == Decimal("60.00")


def test_update_muda_account_ajusta_em_ambas(setup_a) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("20.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    # acc1: 100 + 20 = 120; acc2: 0
    assert _balance(setup_a["acc1_id"]) == Decimal("120.00")
    assert _balance(setup_a["acc2_id"]) == Decimal("0.00")

    with SessionLocal() as db:
        TransactionService(db).update_for_user(
            setup_a["user_id"], tid, TransactionUpdate(account_id=setup_a["acc2_id"])
        )
    # reverte em acc1: 120 - 20 = 100; aplica em acc2: 0 + 20 = 20
    assert _balance(setup_a["acc1_id"]) == Decimal("100.00")
    assert _balance(setup_a["acc2_id"]) == Decimal("20.00")


def test_update_muda_account_e_amount_e_tipo_simultaneamente(setup_a) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("100.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    # acc1: 100+100=200; acc2: 0
    with SessionLocal() as db:
        TransactionService(db).update_for_user(
            setup_a["user_id"],
            tid,
            TransactionUpdate(
                account_id=setup_a["acc2_id"],
                amount=Decimal("30.00"),
                type=TransactionType.EXPENSE,
            ),
        )
    # acc1: 200 - 100 = 100; acc2: 0 + (-30) = -30
    assert _balance(setup_a["acc1_id"]) == Decimal("100.00")
    assert _balance(setup_a["acc2_id"]) == Decimal("-30.00")


def test_update_transacao_de_outro_user_retorna_none(setup_a, user_b_ids) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("10"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id

    with SessionLocal() as db:
        upd = TransactionService(db).update_for_user(
            user_b_ids["user_id"], tid, TransactionUpdate(amount=Decimal("999"))
        )
        assert upd is None


# --------------------------- delete ---------------------------


def test_delete_reverte_saldo(setup_a) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_ex_id"],
                type=TransactionType.EXPENSE,
                amount=Decimal("75.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    assert _balance(setup_a["acc1_id"]) == Decimal("25.00")  # 100 - 75

    with SessionLocal() as db:
        assert TransactionService(db).delete_for_user(setup_a["user_id"], tid) is True
    assert _balance(setup_a["acc1_id"]) == Decimal("100.00")  # voltou


def test_delete_de_outro_user_retorna_false_e_nao_mexe_saldo(setup_a, user_b_ids) -> None:
    with SessionLocal() as db:
        t = TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_ex_id"],
                type=TransactionType.EXPENSE,
                amount=Decimal("10.00"),
                date=date(2026, 5, 23),
            ),
        )
        tid = t.id
    saldo_antes = _balance(setup_a["acc1_id"])

    with SessionLocal() as db:
        assert TransactionService(db).delete_for_user(user_b_ids["user_id"], tid) is False
    assert _balance(setup_a["acc1_id"]) == saldo_antes


# --------------------------- combinacoes ---------------------------


def test_criar_varias_e_validar_soma_final(setup_a) -> None:
    with SessionLocal() as db:
        svc = TransactionService(db)
        for amount, type_ in [
            (Decimal("200"), TransactionType.INCOME),
            (Decimal("50"), TransactionType.EXPENSE),
            (Decimal("30.50"), TransactionType.EXPENSE),
            (Decimal("1000"), TransactionType.INCOME),
            (Decimal("19.50"), TransactionType.EXPENSE),
        ]:
            cat_id = (
                setup_a["cat_in_id"] if type_ == TransactionType.INCOME else setup_a["cat_ex_id"]
            )
            svc.create_for_user(
                setup_a["user_id"],
                TransactionCreate(
                    account_id=setup_a["acc1_id"],
                    category_id=cat_id,
                    type=type_,
                    amount=amount,
                    date=date(2026, 5, 23),
                ),
            )
    # 100 + 200 - 50 - 30.50 + 1000 - 19.50 = 1200
    assert _balance(setup_a["acc1_id"]) == Decimal("1200.00")


def test_concorrencia_sequencial_duas_transacoes(setup_a) -> None:
    """Duas transacoes sequenciais aplicam corretamente sem perda."""
    with SessionLocal() as db:
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("10.00"),
                date=date(2026, 5, 23),
            ),
        )
    with SessionLocal() as db:
        TransactionService(db).create_for_user(
            setup_a["user_id"],
            TransactionCreate(
                account_id=setup_a["acc1_id"],
                category_id=setup_a["cat_in_id"],
                type=TransactionType.INCOME,
                amount=Decimal("10.00"),
                date=date(2026, 5, 23),
            ),
        )
    assert _balance(setup_a["acc1_id"]) == Decimal("120.00")
