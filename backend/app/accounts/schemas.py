"""Schemas Pydantic para Account (S03-T02)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.accounts.models import AccountType


class AccountBase(BaseModel):
    """Campos comuns de entrada de uma conta (S24-T03)."""

    name: str = Field(min_length=1, max_length=80)
    type: AccountType
    initial_balance: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    """Patch parcial: somente campos editaveis pelo usuario."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    type: AccountType | None = None
    is_active: bool | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    current_balance: Decimal
    is_active: bool
    created_at: datetime
