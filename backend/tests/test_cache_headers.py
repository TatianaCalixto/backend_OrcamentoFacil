"""Cache-Control em respostas GET (S25-T05).

Valida o contrato de coordenacao backend+mobile:
- GET autenticado 2xx -> Cache-Control: private, max-age=30;
- health/metrics nao recebem o header (ficam frescos);
- mutacoes nao recebem Cache-Control de cache.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.cache_headers import CACHE_CONTROL_VALUE
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register_and_login(email: str, name: str = "User") -> str:
    r = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "senha123"},
    )
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_autenticado_tem_cache_control() -> None:
    token = _register_and_login("cache-get@ex.com")
    r = client.get("/accounts", headers=_h(token))
    assert r.status_code == 200, r.text
    assert r.headers["Cache-Control"] == CACHE_CONTROL_VALUE
    assert CACHE_CONTROL_VALUE == "private, max-age=30"


def test_healthz_nao_tem_cache_control_de_cache() -> None:
    r = client.get("/healthz")
    assert r.headers.get("Cache-Control") != CACHE_CONTROL_VALUE


def test_mutacao_nao_tem_cache_control() -> None:
    r = client.post(
        "/auth/register",
        json={"name": "Mut", "email": "cache-mut@ex.com", "password": "senha123"},
    )
    assert r.status_code == 201, r.text
    assert r.headers.get("Cache-Control") != CACHE_CONTROL_VALUE
