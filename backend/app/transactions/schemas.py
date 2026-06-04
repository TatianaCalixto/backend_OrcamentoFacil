"""Schemas Pydantic para Transaction (S05-T02)."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.transactions.models import PaymentMethod, TransactionType


class TransactionBase(BaseModel):
    """Campos comuns de entrada de uma transacao (S24-T03)."""

    account_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    date: date_type
    description: str | None = Field(default=None, max_length=500)
    payment_method: PaymentMethod | None = None
    is_recurring: bool = False


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    """Patch parcial. account_id e category_id podem ser trocados.
    A validacao de pertencimento ao usuario fica no service."""

    account_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)
    type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    date: date_type | None = None
    description: str | None = Field(default=None, max_length=500)
    payment_method: PaymentMethod | None = None
    is_recurring: bool | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime


class TransactionPage(BaseModel):
    """Paginacao (S05-T04)."""

    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
