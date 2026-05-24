"""Testes do POST /auth/register (S02-T04)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_registro_feliz_retorna_201_sem_senha() -> None:
    resp = client.post(
        "/auth/register",
        json={"name": "Ana", "email": "ana@ex.com", "password": "senha123"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Ana"
    assert body["email"] == "ana@ex.com"
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_email_normalizado_para_lower_no_registro() -> None:
    resp = client.post(
        "/auth/register",
        json={"name": "Bob", "email": " BOB@EX.COM ", "password": "senha123"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "bob@ex.com"


def test_registro_duplicado_retorna_409() -> None:
    payload = {"name": "Carol", "email": "carol@ex.com", "password": "senha123"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["code"] == "http_409"


def test_payload_invalido_retorna_422() -> None:
    # senha curta demais
    r = client.post(
        "/auth/register",
        json={"name": "X", "email": "x@ex.com", "password": "abc"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_email_sem_arroba_retorna_422() -> None:
    r = client.post(
        "/auth/register",
        json={"name": "Y", "email": "naoeemail", "password": "senha123"},
    )
    assert r.status_code == 422


def test_campos_faltando_retorna_422() -> None:
    r = client.post("/auth/register", json={"email": "z@ex.com"})
    assert r.status_code == 422
