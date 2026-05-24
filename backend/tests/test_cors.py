"""Testes de CORS (S10-T01)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_origin_permitida_recebe_access_control_allow_origin() -> None:
    r = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_origin_nao_permitida_nao_recebe_header() -> None:
    r = client.options(
        "/health",
        headers={
            "Origin": "https://attacker.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette nao retorna o header CORS para origens nao permitidas
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_get_com_origin_permitida_passa() -> None:
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
