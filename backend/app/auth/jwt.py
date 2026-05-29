"""Emissao e verificacao de JWT (S02-T03; refresh em S10-T03)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config import get_settings

TokenKind = Literal["access", "refresh"]


class TokenError(Exception):
    """Erro generico de token (expirado, assinatura invalida, etc.)."""


def _encode(
    user_id: int,
    kind: TokenKind,
    delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + delta).timestamp()),
        "typ": kind,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    user_id: int,
    expires: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    return _encode(
        user_id,
        "access",
        expires or timedelta(minutes=settings.jwt_expire_minutes),
        extra_claims,
    )


def create_refresh_token(
    user_id: int,
    expires: timedelta | None = None,
) -> str:
    settings = get_settings()
    # jti unico permite revogar este refresh especifico no logout (S20-T05).
    return _encode(
        user_id,
        "refresh",
        expires or timedelta(minutes=settings.jwt_refresh_expire_minutes),
        extra_claims={"jti": uuid.uuid4().hex},
    )


def decode_token(token: str, *, expected_typ: TokenKind | None = None) -> dict[str, Any]:
    """Decoda e (opcionalmente) valida que o claim 'typ' bate."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise TokenError(str(e)) from e

    if expected_typ is not None and payload.get("typ") != expected_typ:
        raise TokenError(f"esperado typ={expected_typ}, recebido {payload.get('typ')!r}")
    return payload
