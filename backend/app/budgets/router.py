"""Rotas /budgets (S06-T03)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.budgets.schemas import (
    BudgetCreate,
    BudgetRead,
    BudgetUpdate,
    BudgetWithUsage,
)
from app.budgets.service import BudgetOwnershipError, BudgetService
from app.core.ratelimit import limiter
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/budgets", tags=["budgets"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="orçamento não encontrado")


@router.get("", response_model=list[BudgetWithUsage])
async def list_budgets(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BudgetWithUsage]:
    # default = mes corrente. Paginacao opcional (S24-T06): resposta continua
    # uma lista; default page_size=50 mantem compatibilidade com clientes atuais.
    today = date.today()
    m = month or today.month
    y = year or today.year
    return await BudgetService(db).list_with_usage_for_month(
        current_user.id, m, y, page=page, page_size=page_size
    )


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_budget(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await BudgetService(db).create_for_user(current_user.id, payload)
    except BudgetOwnershipError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{budget_id}", response_model=BudgetWithUsage)
async def get_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = await BudgetService(db).get_with_usage(current_user.id, budget_id)
    if b is None:
        raise _NOT_FOUND
    return b


@router.patch("/{budget_id}", response_model=BudgetRead)
@limiter.limit("10/minute")
async def update_budget(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    budget_id: int,
    payload: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b = await BudgetService(db).update_for_user(current_user.id, budget_id, payload)
    if b is None:
        raise _NOT_FOUND
    return b
