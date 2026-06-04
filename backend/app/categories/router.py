"""Rotas /categories (S04-T03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.categories.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from app.categories.service import CategoryService
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/categories", tags=["categories"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="categoria não encontrada")


@router.get("", response_model=list[CategoryRead])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CategoryService(db).list_for_user(current_user.id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CategoryService(db).create_for_user(current_user.id, payload)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = await CategoryService(db).get_for_user(current_user.id, category_id)
    if cat is None:
        raise _NOT_FOUND
    return cat


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = await CategoryService(db).update_for_user(current_user.id, category_id, payload)
    if cat is None:
        raise _NOT_FOUND
    return cat


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await CategoryService(db).delete_for_user(current_user.id, category_id):
        raise _NOT_FOUND
