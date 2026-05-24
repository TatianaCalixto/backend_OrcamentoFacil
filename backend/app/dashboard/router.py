"""Rotas do Dashboard (Sprint 8)."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.dashboard.schemas import Cashflow, CategoryBreakdown, MonthlySummary
from app.dashboard.service import DashboardService
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _default_month_year(month: int | None, year: int | None) -> tuple[int, int]:
    today = date_type.today()
    return (month or today.month, year or today.year)


@router.get("/monthly-summary", response_model=MonthlySummary)
def monthly_summary(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlySummary:
    m, y = _default_month_year(month, year)
    return DashboardService(db).monthly_summary(current_user.id, m, y)


@router.get("/category-breakdown", response_model=CategoryBreakdown)
def category_breakdown(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CategoryBreakdown:
    m, y = _default_month_year(month, year)
    return DashboardService(db).category_breakdown(current_user.id, m, y)


@router.get("/cashflow", response_model=Cashflow)
def cashflow(
    date_from: date_type = Query(...),
    date_to: date_type = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Cashflow:
    return DashboardService(db).cashflow(current_user.id, date_from, date_to)
