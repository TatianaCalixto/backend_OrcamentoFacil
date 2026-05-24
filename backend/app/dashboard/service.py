"""Service do Dashboard — agregacoes (Sprint 8)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.categories.models import Category
from app.dashboard.schemas import (
    AccountBalance,
    Cashflow,
    CashflowPoint,
    CategoryBreakdown,
    CategoryBreakdownItem,
    MonthlySummary,
)
from app.transactions.models import Transaction, TransactionType


def _month_range(month: int, year: int) -> tuple[date_type, date_type]:
    first = date_type(year, month, 1)
    last = date_type(year, month, monthrange(year, month)[1])
    return first, last


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------ monthly summary ------------------

    def monthly_summary(self, user_id: int, month: int, year: int) -> MonthlySummary:
        first, last = _month_range(month, year)

        # somas por tipo, num unico select
        sum_stmt = select(
            func.coalesce(
                func.sum(
                    case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((Transaction.type == TransactionType.EXPENSE, Transaction.amount), else_=0)
                ),
                0,
            ),
        ).where(
            Transaction.user_id == user_id,
            Transaction.date >= first,
            Transaction.date <= last,
        )
        receita, despesa = self.db.execute(sum_stmt).one()
        receita = Decimal(receita)
        despesa = Decimal(despesa)
        saldo = receita - despesa

        # contas do usuario com saldo corrente
        acc_stmt = (
            select(Account.id, Account.name, Account.current_balance)
            .where(Account.user_id == user_id)
            .order_by(Account.id)
        )
        contas = [
            AccountBalance(account_id=row[0], name=row[1], current_balance=row[2])
            for row in self.db.execute(acc_stmt).all()
        ]

        return MonthlySummary(
            month=month,
            year=year,
            receita_total=receita,
            despesa_total=despesa,
            saldo=saldo,
            contas=contas,
        )

    # ------------------ category breakdown ------------------

    def category_breakdown(self, user_id: int, month: int, year: int) -> CategoryBreakdown:
        first, last = _month_range(month, year)

        stmt = (
            select(
                Category.id,
                Category.name,
                Category.color,
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= first,
                Transaction.date <= last,
            )
            .group_by(Category.id, Category.name, Category.color)
            .order_by(func.coalesce(func.sum(Transaction.amount), 0).desc(), Category.id)
        )
        items = [
            CategoryBreakdownItem(
                category_id=row[0], name=row[1], color=row[2], total=Decimal(row[3])
            )
            for row in self.db.execute(stmt).all()
        ]
        return CategoryBreakdown(month=month, year=year, items=items)

    # ------------------ cashflow ------------------

    def cashflow(self, user_id: int, date_from: date_type, date_to: date_type) -> Cashflow:
        # somas por dia
        stmt = (
            select(
                Transaction.date,
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == TransactionType.INCOME, Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("rec"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == TransactionType.EXPENSE, Transaction.amount),
                            else_=0,
                        )
                    ),
                    0,
                ).label("desp"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= date_from,
                Transaction.date <= date_to,
            )
            .group_by(Transaction.date)
            .order_by(Transaction.date)
        )
        acumulado = Decimal("0")
        points: list[CashflowPoint] = []
        for row in self.db.execute(stmt).all():
            rec = Decimal(row[1])
            desp = Decimal(row[2])
            acumulado += rec - desp
            points.append(
                CashflowPoint(date=row[0], receita=rec, despesa=desp, saldo_acumulado=acumulado)
            )
        return Cashflow(date_from=date_from, date_to=date_to, points=points)
