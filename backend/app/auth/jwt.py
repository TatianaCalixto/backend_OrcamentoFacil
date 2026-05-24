"""Emissao e verificacao de JWT (S02-T03)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


class TokenError(Exception):
    """Erro generico de token (expirado, assinatura invalida, etc.)."""


def create_access_token(
    user_id: int,
    expires: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    delta = expires or timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise TokenError(str(e)) from e
