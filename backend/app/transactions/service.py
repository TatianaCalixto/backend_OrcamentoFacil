"""Service de Transaction (S05-T03).

Regra de negocio CRITICA: ao criar/editar/deletar uma transacao, ajusta
current_balance da conta afetada (receita soma, despesa subtrai).
Mudancas de account_id no update revertem na conta antiga e aplicam na
nova. Mudancas de amount e/ou type tambem propagam.

Toda operacao valida que account e category pertencem ao usuario;
caso contrario levanta OwnershipError (mapeado para 404 pelo router).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounts.models import Account
from app.categories.models import Category
from app.transactions.models import Transaction, TransactionType
from app.transactions.repository import TransactionFilters, TransactionRepository
from app.transactions.schemas import TransactionCreate, TransactionUpdate


class OwnershipError(Exception):
    """Acessou recurso que nao pertence ao usuario (account ou category)."""


def _signed(t_type: TransactionType, amount: Decimal) -> Decimal:
    return amount if t_type == TransactionType.INCOME else -amount


def _signed_txn(t: Transaction) -> Decimal:
    return _signed(t.type, t.amount)


class TransactionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TransactionRepository(db)

    # ------------------ leitura ------------------

    def get_for_user(self, user_id: int, txn_id: int) -> Transaction | None:
        return self.repo.get_for_user(user_id, txn_id)

    def list_for_user(self, user_id: int) -> list[Transaction]:
        return self.repo.list_by_user(user_id)

    def list_paginated(
        self,
        user_id: int,
        filters: TransactionFilters,
        page: int,
        page_size: int,
        order_by: str = "-date",
    ) -> tuple[list[Transaction], int]:
        items = self.repo.list_paginated(user_id, filters, page, page_size, order_by)
        total = self.repo.count(user_id, filters)
        return items, total

    # ------------------ ownership ------------------

    def _account_of(self, user_id: int, account_id: int) -> Account:
        acc = self.db.get(Account, account_id)
        if acc is None or acc.user_id != user_id:
            raise OwnershipError("account nao encontrada ou nao pertence ao usuario")
        return acc

    def _category_of(self, user_id: int, category_id: int) -> Category:
        cat = self.db.get(Category, category_id)
        if cat is None or cat.user_id != user_id:
            raise OwnershipError("category nao encontrada ou nao pertence ao usuario")
        return cat

    # ------------------ create ------------------

    def create_for_user(self, user_id: int, payload: TransactionCreate) -> Transaction:
        account = self._account_of(user_id, payload.account_id)
        self._category_of(user_id, payload.category_id)  # so valida

        txn = Transaction(
            user_id=user_id,
            account_id=payload.account_id,
            category_id=payload.category_id,
            type=payload.type,
            amount=payload.amount,
            date=payload.date,
            description=payload.description,
            payment_method=payload.payment_method,
            is_recurring=payload.is_recurring,
        )
        account.current_balance = account.current_balance + _signed_txn(txn)
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        return txn

    # ------------------ update ------------------

    def update_for_user(
        self, user_id: int, txn_id: int, payload: TransactionUpdate
    ) -> Transaction | None:
        txn = self.repo.get_for_user(user_id, txn_id)
        if txn is None:
            return None

        updates = payload.model_dump(exclude_unset=True)

        # valida nova account/category se vieram
        new_account_id = updates.get("account_id", txn.account_id)
        new_category_id = updates.get("category_id", txn.category_id)
        if "account_id" in updates:
            self._account_of(user_id, new_account_id)
        if "category_id" in updates:
            self._category_of(user_id, new_category_id)

        # snapshot do estado atual (para reverter o saldo da conta antiga)
        old_account_id = txn.account_id
        old_signed = _signed_txn(txn)

        # aplica patch nos campos do txn
        for k, v in updates.items():
            setattr(txn, k, v)
        new_signed = _signed_txn(txn)

        # ajuste de saldo
        if new_account_id == old_account_id:
            # mesma conta: delta = new_signed - old_signed
            account = self._account_of(user_id, old_account_id)
            account.current_balance = account.current_balance + (new_signed - old_signed)
        else:
            old_account = self._account_of(user_id, old_account_id)
            old_account.current_balance = old_account.current_balance - old_signed
            new_account = self._account_of(user_id, new_account_id)
            new_account.current_balance = new_account.current_balance + new_signed

        self.db.commit()
        self.db.refresh(txn)
        return txn

    # ------------------ delete ------------------

    def delete_for_user(self, user_id: int, txn_id: int) -> bool:
        txn = self.repo.get_for_user(user_id, txn_id)
        if txn is None:
            return False
        account = self._account_of(user_id, txn.account_id)
        account.current_balance = account.current_balance - _signed_txn(txn)
        self.db.delete(txn)
        self.db.commit()
        return True
