"""Testes dos schemas de Transaction (S05-T02). Validacoes de shape;
validacao cruzada (account/category do usuario) eh testada em test_transactions_service.py."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.transactions.models import PaymentMethod, TransactionType
from app.transactions.schemas import TransactionCreate, TransactionUpdate


def test_create_aceita_payload_minimo() -> None:
    t = TransactionCreate(
        account_id=1,
        category_id=2,
        type="expense",
        amount=Decimal("9.99"),
        date=date(2026, 5, 23),
    )
    assert t.type == TransactionType.EXPENSE
    assert t.amount == Decimal("9.99")
    assert t.is_recurring is False


def test_create_aceita_todos_os_campos() -> None:
    t = TransactionCreate(
        account_id=1,
        category_id=2,
        type=TransactionType.INCOME,
        amount=Decimal("1000.00"),
        date=date(2026, 5, 23),
        description="Salario",
        payment_method=PaymentMethod.TRANSFER,
        is_recurring=True,
    )
    assert t.payment_method == PaymentMethod.TRANSFER
    assert t.is_recurring is True


def test_create_amount_zero_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            category_id=2,
            type="income",
            amount=Decimal("0"),
            date=date(2026, 5, 23),
        )


def test_create_amount_negativo_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            category_id=2,
            type="expense",
            amount=Decimal("-5"),
            date=date(2026, 5, 23),
        )


def test_create_type_invalido_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            category_id=2,
            type="bitcoin",  # type: ignore[arg-type]
            amount=Decimal("1"),
            date=date(2026, 5, 23),
        )


def test_create_account_id_negativo_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=0,
            category_id=1,
            type="expense",
            amount=Decimal("1"),
            date=date(2026, 5, 23),
        )


def test_create_precisao_excedida_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            category_id=1,
            type="expense",
            amount=Decimal("1.234"),
            date=date(2026, 5, 23),
        )


def test_update_aceita_patch_parcial() -> None:
    u = TransactionUpdate(amount=Decimal("50.00"))
    assert u.amount == Decimal("50.00")
    assert u.account_id is None
    assert u.type is None


def test_update_amount_zero_falha() -> None:
    with pytest.raises(ValidationError):
        TransactionUpdate(amount=Decimal("0"))
