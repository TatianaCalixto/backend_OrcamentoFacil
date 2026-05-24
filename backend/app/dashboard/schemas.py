"""Schemas Pydantic do Dashboard (Sprint 8)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class AccountBalance(BaseModel):
    account_id: int
    name: str
    current_balance: Decimal


class MonthlySummary(BaseModel):
    month: int
    year: int
    receita_total: Decimal
    despesa_total: Decimal
    saldo: Decimal
    contas: list[AccountBalance]


class CategoryBreakdownItem(BaseModel):
    category_id: int
    name: str
    color: str
    total: Decimal


class CategoryBreakdown(BaseModel):
    month: int
    year: int
    items: list[CategoryBreakdownItem]


class CashflowPoint(BaseModel):
    date: date_type
    receita: Decimal
    despesa: Decimal
    saldo_acumulado: Decimal


class Cashflow(BaseModel):
    date_from: date_type
    date_to: date_type
    points: list[CashflowPoint]
