"""Rotas /accounts (S03-T04). Todas exigem autenticacao e sao isoladas por usuario."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.schemas import AccountCreate, AccountRead, AccountUpdate
from app.accounts.service import AccountService
from app.auth.deps import get_current_user
from app.core.ratelimit import limiter
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/accounts", tags=["accounts"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conta não encontrada")


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list:
    return await AccountService(db).list_for_user(current_user.id)


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_account(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AccountService(db).create_for_user(current_user.id, payload)


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = await AccountService(db).get_for_user(current_user.id, account_id)
    if acc is None:
        raise _NOT_FOUND
    return acc


@router.patch("/{account_id}", response_model=AccountRead)
@limiter.limit("10/minute")
async def update_account(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    account_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = await AccountService(db).update_for_user(current_user.id, account_id, payload)
    if acc is None:
        raise _NOT_FOUND
    return acc


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_account(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    deleted = await AccountService(db).delete_for_user(current_user.id, account_id)
    if not deleted:
        raise _NOT_FOUND
