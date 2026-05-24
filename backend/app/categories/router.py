"""Rotas /categories (S04-T03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.categories.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from app.categories.service import CategoryService
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/categories", tags=["categories"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="categoria nao encontrada")


@router.get("", response_model=list[CategoryRead])
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CategoryService(db).list_for_user(current_user.id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return CategoryService(db).create_for_user(current_user.id, payload)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = CategoryService(db).get_for_user(current_user.id, category_id)
    if cat is None:
        raise _NOT_FOUND
    return cat


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = CategoryService(db).update_for_user(current_user.id, category_id, payload)
    if cat is None:
        raise _NOT_FOUND
    return cat


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not CategoryService(db).delete_for_user(current_user.id, category_id):
        raise _NOT_FOUND
