"""Rotas /transactions (S05-T04)."""

from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.ratelimit import limiter
from app.database.session import get_db
from app.transactions.models import TransactionType
from app.transactions.repository import TransactionFilters
from app.transactions.schemas import (
    TransactionCreate,
    TransactionPage,
    TransactionRead,
    TransactionUpdate,
)
from app.transactions.service import OwnershipError, TransactionService
from app.users.models import User

router = APIRouter(prefix="/transactions", tags=["transactions"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="transação não encontrada")


def _handle_ownership(exc: OwnershipError) -> HTTPException:
    # 404 em vez de 403/400 para nao vazar existencia
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=TransactionPage)
async def list_transactions(
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    account_id: int | None = Query(default=None, gt=0),
    category_id: int | None = Query(default=None, gt=0),
    type: TransactionType | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    order_by: str = Query(default="-date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransactionPage:
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        category_id=category_id,
        type=type,
        search=search,
    )
    items, total = await TransactionService(db).list_paginated(
        current_user.id, filters, page, page_size, order_by
    )
    return TransactionPage(
        items=[TransactionRead.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_transaction(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TransactionService(db).create_for_user(current_user.id, payload)
    except OwnershipError as e:
        raise _handle_ownership(e) from e


@router.get("/{txn_id}", response_model=TransactionRead)
async def get_transaction(
    txn_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    t = await TransactionService(db).get_for_user(current_user.id, txn_id)
    if t is None:
        raise _NOT_FOUND
    return t


@router.patch("/{txn_id}", response_model=TransactionRead)
@limiter.limit("60/minute")
async def update_transaction(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    txn_id: int,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        t = await TransactionService(db).update_for_user(current_user.id, txn_id, payload)
    except OwnershipError as e:
        raise _handle_ownership(e) from e
    if t is None:
        raise _NOT_FOUND
    return t


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def delete_transaction(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    txn_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await TransactionService(db).delete_for_user(current_user.id, txn_id):
        raise _NOT_FOUND
