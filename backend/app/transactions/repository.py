"""Repository de Transaction (S05-T03)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.transactions.models import Transaction


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, user_id: int, txn_id: int) -> Transaction | None:
        stmt = select(Transaction).where(Transaction.user_id == user_id, Transaction.id == txn_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_user(self, user_id: int) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
