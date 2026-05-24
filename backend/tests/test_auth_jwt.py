"""Testes do JWT (S02-T03)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from jose import jwt as jose_jwt

from app.auth.jwt import TokenError, create_access_token, decode_token
from app.core.config import get_settings


def test_token_valido_decoda_com_sub_user_id() -> None:
    token = create_access_token(42)
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload and "iat" in payload


def test_token_aceita_extra_claims() -> None:
    token = create_access_token(7, extra_claims={"role": "admin"})
    payload = decode_token(token)
    assert payload["role"] == "admin"


def test_token_expirado_levanta_token_error() -> None:
    token = create_access_token(1, expires=timedelta(seconds=-1))
    with pytest.raises(TokenError):
        decode_token(token)


def test_token_assinado_com_chave_diferente_levanta_token_error() -> None:
    settings = get_settings()
    forged = jose_jwt.encode(
        {"sub": "1", "exp": 9999999999},
        "outra_chave_qualquer",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(TokenError):
        decode_token(forged)


def test_token_lixo_levanta_token_error() -> None:
    with pytest.raises(TokenError):
        decode_token("nao.eh.token")
