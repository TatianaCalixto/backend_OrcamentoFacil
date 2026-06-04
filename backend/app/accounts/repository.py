"""Repository de Account (S03-T03).

Toda query filtra por user_id; queries fora dessa contrato nao existem
neste modulo (isolamento por usuario por construcao).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import Account


class AccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_user(self, user_id: int) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id).order_by(Account.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_for_user(self, user_id: int, account_id: int) -> Account | None:
        stmt = select(Account).where(Account.user_id == user_id, Account.id == account_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add(self, account: Account) -> Account:
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def save(self, account: Account) -> Account:
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def delete(self, account: Account) -> None:
        await self.db.delete(account)
        await self.db.flush()
