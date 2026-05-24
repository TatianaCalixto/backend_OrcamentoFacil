"""Rotas de users (S02-T06)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.users.models import User
from app.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
