"""Rotas /accounts (S03-T04). Todas exigem autenticacao e sao isoladas por usuario."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.accounts.schemas import AccountCreate, AccountRead, AccountUpdate
from app.accounts.service import AccountService
from app.auth.deps import get_current_user
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/accounts", tags=["accounts"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conta nao encontrada")


@router.get("", response_model=list[AccountRead])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    return AccountService(db).list_for_user(current_user.id)


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AccountService(db).create_for_user(current_user.id, payload)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    acc = AccountService(db).get_for_user(current_user.id, account_id)
    if acc is None:
        raise _NOT_FOUND
    return acc


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    acc = AccountService(db).update_for_user(current_user.id, account_id, payload)
    if acc is None:
        raise _NOT_FOUND
    return acc


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = AccountService(db).delete_for_user(current_user.id, account_id)
    if not deleted:
        raise _NOT_FOUND
