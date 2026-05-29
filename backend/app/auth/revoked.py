"""Revogacao de refresh tokens (S20-T05).

- revoke(): marca um jti como revogado (idempotente) — usado no /auth/logout.
- is_revoked(): consultado no /auth/refresh antes de emitir novo par.
- cleanup_expired(): remove registros cujo refresh ja expirou com certeza.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.auth.models import RevokedToken
from app.core.config import get_settings


def is_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None


def revoke(db: Session, jti: str, user_id: int) -> bool:
    """Revoga um jti. Idempotente: retorna False se ja estava revogado."""
    if db.get(RevokedToken, jti) is not None:
        return False
    db.add(RevokedToken(jti=jti, user_id=user_id))
    db.commit()
    return True


def cleanup_expired(db: Session, *, now: datetime | None = None) -> int:
    """Remove registros cujo refresh token ja expirou com certeza.

    Como exp = iat + lifetime e iat <= revoked_at, vale exp <= revoked_at +
    lifetime. Logo, apagar onde revoked_at < now - lifetime garante que o token
    revogado ja esta expirado (e portanto inutil mesmo sem estar na lista).
    Retorna o numero de registros removidos.
    """
    settings = get_settings()
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(minutes=settings.jwt_refresh_expire_minutes)
    result = db.execute(delete(RevokedToken).where(RevokedToken.revoked_at < cutoff))
    db.commit()
    return result.rowcount or 0
