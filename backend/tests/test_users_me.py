"""Testes do GET /users/me (S02-T06)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth.jwt import create_access_token
from app.database.session import SessionLocal
from app.main import app
from app.users.models import User

client = TestClient(app, raise_server_exceptions=False)


def _register_and_login() -> tuple[int, str]:
    payload = {"name": "Ana", "email": "ana@ex.com", "password": "senha123"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 201
    user_id = r.json()["id"]
    r = client.post(
        "/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert r.status_code == 200
    return user_id, r.json()["access_token"]


def test_me_com_token_valido_retorna_usuario() -> None:
    user_id, token = _register_and_login()
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == user_id
    assert body["email"] == "ana@ex.com"
    assert "password" not in body and "password_hash" not in body


def test_me_sem_header_retorna_401() -> None:
    r = client.get("/users/me")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower() == "bearer"


def test_me_com_token_aleatorio_retorna_401() -> None:
    r = client.get("/users/me", headers={"Authorization": "Bearer nao.eh.token"})
    assert r.status_code == 401


def test_me_com_token_expirado_retorna_401() -> None:
    token = create_access_token(999, expires=timedelta(seconds=-1))
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_me_com_token_de_usuario_deletado_retorna_401() -> None:
    user_id, token = _register_and_login()
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("scheme", ["Token", "Basic"])
def test_me_com_scheme_errado_retorna_401(scheme: str) -> None:
    _, token = _register_and_login()
    r = client.get("/users/me", headers={"Authorization": f"{scheme} {token}"})
    assert r.status_code == 401


def test_me_com_token_sem_sub_numerico_retorna_401() -> None:
    """Cobre a guarda contra payload['sub'] ausente/nao numerico em get_current_user."""
    # cria um token "valido" mas com sub nao numerico via override no payload
    from datetime import UTC, datetime, timedelta

    from jose import jwt as jose_jwt

    from app.auth.jwt import create_access_token
    from app.core.config import get_settings

    settings = get_settings()
    now = datetime.now(UTC)
    forged = jose_jwt.encode(
        {
            "sub": "abc",  # nao e digito
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.get("/users/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    # sanity: token bem-formado (so para reforcar que o 401 veio da guarda do sub)
    assert create_access_token(1)  # nao levanta
