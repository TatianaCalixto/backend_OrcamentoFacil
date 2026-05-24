"""Repository de Account (S03-T03).

Toda query filtra por user_id; queries fora dessa contrato nao existem
neste modulo (isolamento por usuario por construcao).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import Account


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: int) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id).order_by(Account.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_for_user(self, user_id: int, account_id: int) -> Account | None:
        stmt = select(Account).where(Account.user_id == user_id, Account.id == account_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, account: Account) -> Account:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def save(self, account: Account) -> Account:
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account: Account) -> None:
        self.db.delete(account)
        self.db.commit()
