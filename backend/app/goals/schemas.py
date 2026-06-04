"""Schemas Pydantic para Goal (S07-T02)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.goals.models import GoalStatus


class GoalBase(BaseModel):
    """Campos comuns de entrada de uma meta (S24-T03)."""

    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    deadline: date_type | None = None


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deadline: date_type | None = None


class GoalRead(GoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: GoalStatus
