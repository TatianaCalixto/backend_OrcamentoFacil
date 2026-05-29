"""Headers de seguranca HTTP (S20-T04).

Valida os 4 headers base em qualquer resposta (inclusive 404) e que o HSTS
so e enviado quando production=True.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security_headers import (
    BASE_SECURITY_HEADERS,
    HSTS_HEADER,
    HSTS_VALUE,
    SecurityHeadersMiddleware,
)
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_headers_base_presentes_no_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["Content-Security-Policy"] == "default-src 'self'"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_headers_presentes_ate_em_404() -> None:
    r = client.get("/rota-inexistente")
    assert r.status_code == 404
    for name in BASE_SECURITY_HEADERS:
        assert name in r.headers


def test_hsts_ausente_fora_de_producao() -> None:
    # o app real roda com ENVIRONMENT=test (conftest) -> sem HSTS
    r = client.get("/health")
    assert HSTS_HEADER not in r.headers


def _mini_client(production: bool) -> TestClient:
    mini = FastAPI()
    mini.add_middleware(SecurityHeadersMiddleware, production=production)

    @mini.get("/x")
    def _x() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(mini)


def test_hsts_presente_em_producao() -> None:
    r = _mini_client(production=True).get("/x")
    assert r.headers[HSTS_HEADER] == HSTS_VALUE
    for name in BASE_SECURITY_HEADERS:
        assert name in r.headers


def test_hsts_ausente_quando_middleware_nao_producao() -> None:
    r = _mini_client(production=False).get("/x")
    assert HSTS_HEADER not in r.headers
    for name in BASE_SECURITY_HEADERS:
        assert name in r.headers
