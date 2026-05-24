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


def test_me_com_token_de_usuario_deletado_retorna_401() -> None:
    user_id, token = _register_and_login()
    with SessionLocal() as db:
        db.execute(delete(User).where(User.id == user_id))
        db.commit()
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("scheme", ["Token", "Basic"])
def test_me_com_scheme_errado_retorna_401(scheme: str) -> None:
    _, token = _register_and_login()
    r = client.get("/users/me", headers={"Authorization": f"{scheme} {token}"})
    assert r.status_code == 401
