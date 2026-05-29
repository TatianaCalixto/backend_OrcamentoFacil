"""Rotas /budgets (S06-T03)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

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

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budget nao encontrado")


@router.get("", response_model=list[BudgetWithUsage])
def list_budgets(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BudgetWithUsage]:
    # default = mes corrente
    today = date.today()
    m = month or today.month
    y = year or today.year
    return BudgetService(db).list_with_usage_for_month(current_user.id, m, y)


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_budget(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return BudgetService(db).create_for_user(current_user.id, payload)
    except BudgetOwnershipError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/{budget_id}", response_model=BudgetWithUsage)
def get_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = BudgetService(db).get_with_usage(current_user.id, budget_id)
    if b is None:
        raise _NOT_FOUND
    return b


@router.patch("/{budget_id}", response_model=BudgetRead)
@limiter.limit("10/minute")
def update_budget(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    budget_id: int,
    payload: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = BudgetService(db).update_for_user(current_user.id, budget_id, payload)
    if b is None:
        raise _NOT_FOUND
    return b
