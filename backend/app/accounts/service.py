"""Service de Account (S03-T03).

Aplica regras de negocio (ex.: current_balance inicia igual ao
initial_balance) e delega persistencia ao AccountRepository.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.accounts.repository import AccountRepository
from app.accounts.schemas import AccountCreate, AccountUpdate


class AccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AccountRepository(db)

    def list_for_user(self, user_id: int) -> list[Account]:
        return self.repo.list_by_user(user_id)

    def get_for_user(self, user_id: int, account_id: int) -> Account | None:
        return self.repo.get_for_user(user_id, account_id)

    def create_for_user(self, user_id: int, payload: AccountCreate) -> Account:
        account = Account(
            user_id=user_id,
            name=payload.name,
            type=payload.type,
            initial_balance=payload.initial_balance,
            current_balance=payload.initial_balance,  # regra: arranca igual
        )
        return self.repo.add(account)

    def update_for_user(
        self, user_id: int, account_id: int, payload: AccountUpdate
    ) -> Account | None:
        account = self.repo.get_for_user(user_id, account_id)
        if account is None:
            return None
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(account, key, value)
        return self.repo.save(account)

    def delete_for_user(self, user_id: int, account_id: int) -> bool:
        account = self.repo.get_for_user(user_id, account_id)
        if account is None:
            return False
        self.repo.delete(account)
        return True
