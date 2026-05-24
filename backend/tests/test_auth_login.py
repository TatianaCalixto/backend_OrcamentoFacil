"""Testes do POST /auth/login (S02-T05)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import decode_token
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def usuario_registrado() -> dict[str, str]:
    payload = {"name": "Ana", "email": "ana@ex.com", "password": "senha123"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 201
    return payload


def test_login_feliz_retorna_token_bearer(usuario_registrado: dict[str, str]) -> None:
    r = client.post(
        "/auth/login",
        json={
            "email": usuario_registrado["email"],
            "password": usuario_registrado["password"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    # token e valido e tem sub = id do usuario
    payload = decode_token(body["access_token"])
    assert payload["sub"].isdigit()


def test_login_normaliza_email_para_lower(usuario_registrado: dict[str, str]) -> None:
    r = client.post(
        "/auth/login",
        json={
            "email": " ANA@EX.COM ",
            "password": usuario_registrado["password"],
        },
    )
    assert r.status_code == 200


def test_login_com_senha_errada_retorna_401(usuario_registrado: dict[str, str]) -> None:
    r = client.post(
        "/auth/login",
        json={"email": usuario_registrado["email"], "password": "senha_errada"},
    )
    assert r.status_code == 401
    assert r.json()["code"] == "http_401"


def test_login_com_email_inexistente_retorna_401() -> None:
    r = client.post(
        "/auth/login",
        json={"email": "ninguem@ex.com", "password": "qualquer"},
    )
    assert r.status_code == 401


def test_login_payload_invalido_retorna_422() -> None:
    r = client.post("/auth/login", json={"email": "x@y.com"})
    assert r.status_code == 422


def test_login_resposta_inclui_header_www_authenticate_em_401() -> None:
    r = client.post(
        "/auth/login",
        json={"email": "ninguem@ex.com", "password": "x"},
    )
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower() == "bearer"
