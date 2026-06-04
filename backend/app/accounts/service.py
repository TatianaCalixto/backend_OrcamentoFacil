"""Service de Account (S03-T03).

Aplica regras de negocio (ex.: current_balance inicia igual ao
initial_balance) e delega persistencia ao AccountRepository.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import Account
from app.accounts.repository import AccountRepository
from app.accounts.schemas import AccountCreate, AccountUpdate


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AccountRepository(db)

    async def list_for_user(self, user_id: int) -> list[Account]:
        return await self.repo.list_by_user(user_id)

    async def get_for_user(self, user_id: int, account_id: int) -> Account | None:
        return await self.repo.get_for_user(user_id, account_id)

    async def create_for_user(self, user_id: int, payload: AccountCreate) -> Account:
        account = Account(
            user_id=user_id,
            name=payload.name,
            type=payload.type,
            initial_balance=payload.initial_balance,
            current_balance=payload.initial_balance,  # regra: arranca igual
        )
        return await self.repo.add(account)

    async def update_for_user(
        self, user_id: int, account_id: int, payload: AccountUpdate
    ) -> Account | None:
        account = await self.repo.get_for_user(user_id, account_id)
        if account is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(account, key, value)
        return await self.repo.save(account)

    async def delete_for_user(self, user_id: int, account_id: int) -> bool:
        account = await self.repo.get_for_user(user_id, account_id)
        if account is None:
            return False
        await self.repo.delete(account)
        return True
