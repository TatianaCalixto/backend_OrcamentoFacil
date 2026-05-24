"""Testes dos schemas de Account (S03-T02)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.accounts.models import AccountType
from app.accounts.schemas import AccountCreate, AccountUpdate


def test_account_create_aceita_tipo_valido() -> None:
    c = AccountCreate(name="Nubank", type="checking", initial_balance=Decimal("100.50"))
    assert c.type == AccountType.CHECKING
    assert c.initial_balance == Decimal("100.50")


def test_account_create_default_balance_zero() -> None:
    c = AccountCreate(name="X", type=AccountType.CASH)
    assert c.initial_balance == Decimal("0")


def test_account_create_tipo_desconhecido_levanta_validation_error() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(name="X", type="bitcoin")  # type: ignore[arg-type]


def test_account_create_nome_vazio_levanta_validation_error() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(name="", type=AccountType.CASH)


def test_account_create_balance_acima_da_precisao_falha() -> None:
    with pytest.raises(ValidationError):
        AccountCreate(
            name="X", type=AccountType.CASH, initial_balance=Decimal("123456789012345.00")
        )


def test_account_update_aceita_patch_parcial() -> None:
    u = AccountUpdate(name="Novo nome")
    assert u.name == "Novo nome"
    assert u.type is None
    assert u.is_active is None


def test_account_update_aceita_apenas_is_active() -> None:
    u = AccountUpdate(is_active=False)
    assert u.is_active is False


def test_account_update_tipo_invalido_falha() -> None:
    with pytest.raises(ValidationError):
        AccountUpdate(type="bitcoin")  # type: ignore[arg-type]
