"""Schemas Pydantic para Goal (S07-T02)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.goals.models import GoalStatus


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    deadline: date_type | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    current_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    deadline: date_type | None = None


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date_type | None
    status: GoalStatus
