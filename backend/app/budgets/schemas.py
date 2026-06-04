"""Schemas Pydantic para Budget (S06-T02 e S06-T03)."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BudgetStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


def status_for(percent_used: Decimal) -> BudgetStatus:
    """Regra de alerta: >100% critical, >80% warning, senao ok."""
    if percent_used > Decimal("100"):
        return BudgetStatus.CRITICAL
    if percent_used > Decimal("80"):
        return BudgetStatus.WARNING
    return BudgetStatus.OK


class BudgetBase(BaseModel):
    """Campos comuns de entrada de um orcamento (S24-T03)."""

    category_id: int = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)
    limit_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    limit_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)


class BudgetRead(BudgetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class BudgetWithUsage(BudgetRead):
    """Budget enriquecido com o uso calculado para o mes/ano corrente do budget."""

    used_amount: Decimal
    percent_used: Decimal
    status: BudgetStatus
