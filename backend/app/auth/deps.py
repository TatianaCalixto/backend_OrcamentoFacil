"""Dependencies de autenticacao (S02-T06)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import TokenError, decode_token
from app.database.session import get_db
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="nao autenticado",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _UNAUTH
    try:
        # tokens antigos (S02-T03) nao tinham 'typ'; toleramos isso para nao
        # quebrar tokens emitidos antes do refresh. Apos S10-T03, tokens
        # marcados como refresh sao explicitamente rejeitados.
        payload = decode_token(token)
        if payload.get("typ") == "refresh":
            raise TokenError("refresh token nao pode ser usado como access")
    except TokenError as e:
        raise _UNAUTH from e

    sub = payload.get("sub")
    if not sub or not str(sub).isdigit():
        raise _UNAUTH

    user = db.get(User, int(sub))
    if user is None:
        raise _UNAUTH
    return user
