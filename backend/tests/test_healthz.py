"""Healthcheck profundo /healthz (S21-T04).

GET (convencao de health probe; ver DEC-005). DB ok -> 200 com latencia;
DB down -> 503; nao expoe credenciais/string de conexao.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.database.session import get_db
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class _BoomSession:
    """Session falsa cujo execute simula banco indisponivel."""

    def execute(self, *args, **kwargs):
        raise RuntimeError("conexao com o banco recusada")

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def _boom_db():
    yield _BoomSession()


def test_healthz_db_ok_200() -> None:
    r = client.get("/healthz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert isinstance(body["uptime_seconds"], (int, float))
    assert body["database"]["status"] == "up"
    assert isinstance(body["database"]["latency_ms"], (int, float))


def test_healthz_db_down_503() -> None:
    app.dependency_overrides[get_db] = _boom_db
    try:
        r = client.get("/healthz")
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["database"]["status"] == "down"
    assert body["database"]["latency_ms"] is None


def test_healthz_nao_expoe_segredos() -> None:
    txt = client.get("/healthz").text.lower()
    for leak in ("password", "postgres", "sqlite", "://", "secret"):
        assert leak not in txt


def test_healthz_distinto_de_health() -> None:
    h = client.get("/health").json()
    hz = client.get("/healthz").json()
    assert set(h.keys()) == {"status", "version"}
    assert "database" in hz and "uptime_seconds" in hz
