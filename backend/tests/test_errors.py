"""Testes dos exception handlers globais e request_id (S01-T05)."""

from __future__ import annotations

import logging
import re
import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import REQUEST_ID_HEADER, register_error_handlers
from app.core.logging import JsonFormatter, TextFormatter, configure_logging


def _make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("kaboom")

    @app.get("/teapot")
    async def teapot() -> None:
        raise HTTPException(status_code=418, detail="sou um bule")

    class _Payload(BaseModel):
        n: int

    @app.post("/echo")
    async def echo(p: _Payload) -> dict[str, int]:
        return {"n": p.n}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_make_app(), raise_server_exceptions=False)


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


def test_request_id_e_gerado_e_propagado_no_header(client: TestClient) -> None:
    resp = client.get("/ok")
    assert resp.status_code == 200
    rid = resp.headers.get(REQUEST_ID_HEADER)
    assert rid is not None and _is_uuid(rid)


def test_request_id_de_entrada_e_respeitado(client: TestClient) -> None:
    rid_in = "test-rid-123"
    resp = client.get("/ok", headers={REQUEST_ID_HEADER: rid_in})
    assert resp.headers[REQUEST_ID_HEADER] == rid_in


def test_http_exception_tem_payload_padronizado(client: TestClient) -> None:
    resp = client.get("/teapot")
    assert resp.status_code == 418
    body = resp.json()
    assert body["detail"] == "sou um bule"
    assert body["code"] == "http_418"
    assert _is_uuid(body["request_id"])
    assert body["request_id"] == resp.headers[REQUEST_ID_HEADER]


def test_validation_error_422_tem_payload_padronizado(client: TestClient) -> None:
    resp = client.post("/echo", json={"n": "nao-eh-numero"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["detail"], list) and len(body["detail"]) >= 1
    assert _is_uuid(body["request_id"])


def test_unhandled_exception_500_tem_payload_padronizado(
    client: TestClient,
) -> None:
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "erro interno do servidor"
    assert body["code"] == "internal_error"
    assert _is_uuid(body["request_id"])


def test_log_de_500_contem_request_id(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="orcafacil"):
        resp = client.get("/boom")
    rid = resp.json()["request_id"]
    # ao menos um log deve carregar o request_id como extra
    rids = [getattr(r, "request_id", None) for r in caplog.records]
    assert rid in rids


def test_configure_logging_json_em_production() -> None:
    configure_logging("production")
    root = logging.getLogger()
    assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers if h.formatter)


def test_configure_logging_texto_em_development() -> None:
    configure_logging("development")
    root = logging.getLogger()
    assert any(isinstance(h.formatter, TextFormatter) for h in root.handlers if h.formatter)


def test_json_formatter_inclui_request_id_quando_extra() -> None:
    import io

    handler = logging.StreamHandler(io.StringIO())
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("orcafacil.test.fmt")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.info("teste %s", "x", extra={"request_id": "abc123"})

    output = handler.stream.getvalue().strip()
    assert re.search(r'"request_id"\s*:\s*"abc123"', output)
    assert '"msg": "teste x"' in output
