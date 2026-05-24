"""Testes de rate limit em /auth/login e /auth/register (S10-T02).

O limite e 10/minuto por IP. Como o limiter eh reset entre testes
(conftest._reset_rate_limit), aqui podemos estourar o limite sem
contaminar outros testes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_register_dispara_429_apos_10_chamadas() -> None:
    for i in range(10):
        # nao importa se o registro falhou (422/409): o decorator do slowapi
        # incrementa o contador independentemente do resultado.
        client.post(
            "/auth/register",
            json={"name": f"U{i}", "email": f"u{i}@ex.com", "password": "senha123"},
        )
    # 11a deve estourar
    r = client.post(
        "/auth/register",
        json={"name": "X", "email": "x@ex.com", "password": "senha123"},
    )
    assert r.status_code == 429


def test_login_dispara_429_apos_10_chamadas() -> None:
    for _ in range(10):
        client.post("/auth/login", json={"email": "x@ex.com", "password": "z"})
    r = client.post("/auth/login", json={"email": "x@ex.com", "password": "z"})
    assert r.status_code == 429
