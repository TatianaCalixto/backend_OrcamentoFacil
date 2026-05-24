"""Testes do refresh token (S10-T03)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.auth.jwt import create_refresh_token
from app.database.session import SessionLocal
from app.main import app
from app.users.models import User

client = TestClient(app, raise_server_exceptions=False)


def _register_login(email: str) -> tuple[str, str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    j = r.json()
    return j["access_token"], j["refresh_token"], uid


def test_login_devolve_refresh_token() -> None:
    a, refresh, _uid = _register_login("a@ex.com")
    assert isinstance(a, str) and a
    assert isinstance(refresh, str) and refresh
    assert a != refresh


def test_refresh_emite_novos_tokens() -> None:
    _a, refresh, _uid = _register_login("a@ex.com")
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    j = r.json()
    assert j["access_token"] and j["refresh_token"]
    assert j["token_type"] == "bearer"


def test_refresh_invalido_401() -> None:
    r = client.post("/auth/refresh", json={"refresh_token": "lixo.nao.eh.token"})
    assert r.status_code == 401


def test_refresh_expirado_401() -> None:
    # cria um refresh expirado para user 1
    token = create_refresh_token(1, expires=timedelta(seconds=-1))
    r = client.post("/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 401


def test_access_token_nao_serve_como_refresh() -> None:
    access, _refresh, _uid = _register_login("a@ex.com")
    r = client.post("/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


def test_refresh_token_nao_serve_como_access() -> None:
    _a, refresh, _uid = _register_login("a@ex.com")
    r = client.get("/users/me", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


def test_refresh_de_user_deletado_401() -> None:
    _a, refresh, uid = _register_login("a@ex.com")
    with SessionLocal() as db:
        u = db.get(User, uid)
        db.delete(u)
        db.commit()
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401
