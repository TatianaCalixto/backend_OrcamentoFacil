"""Rotas de autenticacao (S02-T04 register; S02-T05 login;
S10-T02 rate limit; S10-T03 refresh)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.revoked import cleanup_expired, is_revoked, revoke
from app.auth.security import hash_password, verify_password
from app.categories.seed import seed_default_categories
from app.core.ratelimit import limiter
from app.database.session import get_db
from app.users.models import User
from app.users.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo usuario",
    description="Cria um usuario, faz seed automatico das 8 categorias padrao "
    "e retorna o UserRead. Email duplicado retorna 409.",
)
@limiter.limit("10/minute")
def register(
    request: Request,  # noqa: ARG001 — exigido pelo slowapi
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email ja cadastrado",
        )
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    seed_default_categories(db, user.id)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica e devolve access + refresh tokens",
    description="POST com email+password. Em sucesso retorna 200 com access_token e refresh_token. "
    "Em falha retorna 401 com header WWW-Authenticate: Bearer.",
)
@limiter.limit("10/minute")
def login(
    request: Request,  # noqa: ARG001
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais invalidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Emite novo par de tokens a partir de um refresh valido",
    description="Recebe {refresh_token}. Se valido (typ=refresh, nao expirado, "
    "assinatura ok, usuario ainda existe), retorna novo par; senao 401.",
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    unauth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="refresh token invalido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = decode_token(payload.refresh_token, expected_typ="refresh")
    except TokenError as e:
        raise unauth from e
    sub = claims.get("sub")
    if not sub or not str(sub).isdigit():
        raise unauth
    # refresh revogado (logout) nao pode emitir novo par (S20-T05).
    jti = claims.get("jti")
    if jti and is_revoked(db, jti):
        raise unauth
    user = db.get(User, int(sub))
    if user is None:
        raise unauth
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post(
    "/logout",
    summary="Revoga o refresh token atual (logout)",
    description="Autenticado (Bearer access). Recebe {refresh_token} e revoga seu "
    "jti, impedindo emissao de novos tokens a partir dele. Idempotente: refresh "
    "invalido/expirado ou sem jti retorna 200 sem erro.",
)
def logout(
    payload: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        claims = decode_token(payload.refresh_token, expected_typ="refresh")
    except TokenError:
        # nada a revogar (logout idempotente)
        return {"detail": "nenhum refresh ativo para revogar"}
    if str(claims.get("sub")) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token nao pertence ao usuario autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = claims.get("jti")
    if not jti:
        return {"detail": "refresh sem jti (token antigo); nada a revogar"}
    revoke(db, jti, current_user.id)
    # limpeza oportunistica de registros ja expirados (cleanup on-demand)
    cleanup_expired(db)
    return {"detail": "logout efetuado"}
