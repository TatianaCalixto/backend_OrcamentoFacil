"""Service de Goal (S07-T02). Aplica regra de status automatico."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.goals.models import Goal, GoalStatus
from app.goals.schemas import GoalCreate, GoalUpdate


def _status_for(current: object, target: object) -> GoalStatus:
    return GoalStatus.COMPLETED if current >= target else GoalStatus.IN_PROGRESS


class GoalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----------------- read -----------------

    def list_for_user(self, user_id: int) -> list[Goal]:
        stmt = select(Goal).where(Goal.user_id == user_id).order_by(Goal.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_for_user(self, user_id: int, goal_id: int) -> Goal | None:
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.id == goal_id)
        return self.db.execute(stmt).scalar_one_or_none()

    # ----------------- create -----------------

    def create_for_user(self, user_id: int, payload: GoalCreate) -> Goal:
        g = Goal(
            user_id=user_id,
            name=payload.name,
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            deadline=payload.deadline,
            status=_status_for(payload.current_amount, payload.target_amount),
        )
        self.db.add(g)
        self.db.commit()
        self.db.refresh(g)
        return g

    # ----------------- update -----------------

    def update_for_user(self, user_id: int, goal_id: int, payload: GoalUpdate) -> Goal | None:
        g = self.get_for_user(user_id, goal_id)
        if g is None:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(g, k, v)
        # recalcula status sempre apos qualquer mudanca relevante
        g.status = _status_for(g.current_amount, g.target_amount)
        self.db.commit()
        self.db.refresh(g)
        return g

    # ----------------- delete -----------------

    def delete_for_user(self, user_id: int, goal_id: int) -> bool:
        g = self.get_for_user(user_id, goal_id)
        if g is None:
            return False
        self.db.delete(g)
        self.db.commit()
        return True
