"""Service de import CSV (Sprint 9). Cria transacoes em batch e atualiza saldo
da conta em UMA UNICA gravacao por chamada.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.models import Account
from app.categories.models import Category
from app.imports.parser import (
    FALLBACK_CATEGORY_NAME,
    ParseError,
    ParseResult,
    parse_csv,
)
from app.imports.schemas import ImportError as ImportErrorSchema
from app.imports.schemas import ImportResult
from app.transactions.models import Transaction, TransactionType


class CsvImportOwnershipError(Exception):
    """Conta nao pertence ao usuario."""


class CsvImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _account_of(self, user_id: int, account_id: int) -> Account:
        acc = await self.db.get(Account, account_id)
        if acc is None or acc.user_id != user_id:
            raise CsvImportOwnershipError("conta não pertence ao usuário")
        return acc

    async def _user_categories_by_name(self, user_id: int) -> dict[str, Category]:
        stmt = select(Category).where(Category.user_id == user_id)
        return {c.name: c for c in (await self.db.execute(stmt)).scalars().all()}

    async def import_csv(self, user_id: int, account_id: int, content: bytes) -> ImportResult:
        account = await self._account_of(user_id, account_id)
        parsed: ParseResult = parse_csv(content)

        categorias = await self._user_categories_by_name(user_id)

        novas: list[Transaction] = []
        skipped_errors: list[ParseError] = list(parsed.errors)
        delta = Decimal("0")

        for line in parsed.rows:
            cat = categorias.get(line.suggested_category_name) or categorias.get(
                FALLBACK_CATEGORY_NAME
            )
            if cat is None:
                skipped_errors.append(
                    ParseError(
                        line_number=line.line_number,
                        message=(
                            f"categoria '{line.suggested_category_name}' e a categoria "
                            f"padrão '{FALLBACK_CATEGORY_NAME}' não existem para o usuário"
                        ),
                    )
                )
                continue
            txn = Transaction(
                user_id=user_id,
                account_id=account.id,
                category_id=cat.id,
                type=line.type,
                amount=line.amount,
                date=line.date,
                description=line.description,
            )
            novas.append(txn)
            delta += line.amount if line.type == TransactionType.INCOME else -line.amount

        # UoW (S24-T02): apenas flush; o commit/rollback fica na borda (get_db).
        if novas:
            self.db.add_all(novas)
            account.current_balance = account.current_balance + delta
            await self.db.flush()
            for n in novas:
                await self.db.refresh(n)

        return ImportResult(
            created_count=len(novas),
            skipped_count=len(skipped_errors),
            errors=[
                ImportErrorSchema(line_number=e.line_number, message=e.message)
                for e in skipped_errors
            ],
        )
