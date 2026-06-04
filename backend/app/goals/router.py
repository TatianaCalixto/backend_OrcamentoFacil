"""Rotas /goals (S07-T02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.ratelimit import limiter
from app.database.session import get_db
from app.goals.schemas import GoalCreate, GoalRead, GoalUpdate
from app.goals.service import GoalService
from app.users.models import User

router = APIRouter(prefix="/goals", tags=["goals"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="meta não encontrada")


@router.get("", response_model=list[GoalRead])
async def list_goals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Paginacao opcional (S24-T06): resposta continua uma lista; default
    # page_size=50 mantem compatibilidade com clientes atuais.
    return await GoalService(db).list_for_user(current_user.id, page=page, page_size=page_size)


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_goal(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalService(db).create_for_user(current_user.id, payload)


@router.get("/{goal_id}", response_model=GoalRead)
async def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await GoalService(db).get_for_user(current_user.id, goal_id)
    if g is None:
        raise _NOT_FOUND
    return g


@router.patch("/{goal_id}", response_model=GoalRead)
@limiter.limit("10/minute")
async def update_goal(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    goal_id: int,
    payload: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = await GoalService(db).update_for_user(current_user.id, goal_id, payload)
    if g is None:
        raise _NOT_FOUND
    return g


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_goal(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await GoalService(db).delete_for_user(current_user.id, goal_id):
        raise _NOT_FOUND
