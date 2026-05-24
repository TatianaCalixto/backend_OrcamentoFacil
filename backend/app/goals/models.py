"""Model Goal (S07-T01)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class GoalStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    deadline: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus, name="goal_status"), nullable=False, default=GoalStatus.IN_PROGRESS
    )

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goals_target_positive"),
        CheckConstraint("current_amount >= 0", name="ck_goals_current_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Goal id={self.id} name={self.name!r} {self.current_amount}/{self.target_amount}>"
