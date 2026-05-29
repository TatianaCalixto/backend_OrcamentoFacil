"""Models de autenticacao — revogacao de refresh token (S20-T05).

revoked_tokens guarda o jti dos refresh tokens revogados (logout). O
/auth/refresh consulta essa tabela antes de emitir novo par. Cleanup remove
registros cujo refresh ja expirou com certeza (ver app.auth.revoked).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<RevokedToken jti={self.jti!r} user_id={self.user_id}>"
