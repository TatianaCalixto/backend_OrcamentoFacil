"""Service de Goal (S07-T02). Aplica regra de status automatico."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.goals.models import Goal, GoalStatus
from app.goals.schemas import GoalCreate, GoalUpdate


def _status_for(current: object, target: object) -> GoalStatus:
    return GoalStatus.COMPLETED if current >= target else GoalStatus.IN_PROGRESS


class GoalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------- read -----------------

    async def list_for_user(self, user_id: int, page: int = 1, page_size: int = 50) -> list[Goal]:
        # order_by(id): mais antigos primeiro (S24-T06). Paginacao opcional;
        # default page_size=50 mantem compatibilidade (poucos goals por usuario).
        stmt = (
            select(Goal)
            .where(Goal.user_id == user_id)
            .order_by(Goal.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_for_user(self, user_id: int, goal_id: int) -> Goal | None:
        stmt = select(Goal).where(Goal.user_id == user_id, Goal.id == goal_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # ----------------- create -----------------

    async def create_for_user(self, user_id: int, payload: GoalCreate) -> Goal:
        g = Goal(
            user_id=user_id,
            name=payload.name,
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            deadline=payload.deadline,
            status=_status_for(payload.current_amount, payload.target_amount),
        )
        self.db.add(g)
        await self.db.flush()
        await self.db.refresh(g)
        return g

    # ----------------- update -----------------

    async def update_for_user(self, user_id: int, goal_id: int, payload: GoalUpdate) -> Goal | None:
        g = await self.get_for_user(user_id, goal_id)
        if g is None:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(g, k, v)
        # recalcula status sempre apos qualquer mudanca relevante
        g.status = _status_for(g.current_amount, g.target_amount)
        await self.db.flush()
        await self.db.refresh(g)
        return g

    # ----------------- delete -----------------

    async def delete_for_user(self, user_id: int, goal_id: int) -> bool:
        g = await self.get_for_user(user_id, goal_id)
        if g is None:
            return False
        await self.db.delete(g)
        await self.db.flush()
        return True
