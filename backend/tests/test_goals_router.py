"""Testes /goals (S07-T02). Foca na regra de status automatico."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register(email: str) -> str:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token_a() -> str:
    return _register("a@ex.com")


@pytest.fixture
def token_b() -> str:
    return _register("b@ex.com")


def test_create_inicia_in_progress(token_a: str) -> None:
    r = client.post(
        "/goals",
        headers=_h(token_a),
        json={"name": "Reserva", "target_amount": "1000.00"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "in_progress"
    assert body["current_amount"] == "0.00"


def test_create_com_current_igual_target_marca_completed(token_a: str) -> None:
    r = client.post(
        "/goals",
        headers=_h(token_a),
        json={"name": "Viagem", "target_amount": "500", "current_amount": "500"},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "completed"


def test_patch_para_current_maior_que_target_marca_completed(token_a: str) -> None:
    r = client.post(
        "/goals",
        headers=_h(token_a),
        json={"name": "X", "target_amount": "100", "current_amount": "50"},
    )
    gid = r.json()["id"]
    r = client.patch(f"/goals/{gid}", headers=_h(token_a), json={"current_amount": "120"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_patch_voltando_current_abaixo_marca_in_progress(token_a: str) -> None:
    """Reverte status COMPLETED -> IN_PROGRESS quando current cai abaixo do target."""
    r = client.post(
        "/goals",
        headers=_h(token_a),
        json={"name": "X", "target_amount": "100", "current_amount": "100"},
    )
    gid = r.json()["id"]
    assert r.json()["status"] == "completed"

    r = client.patch(f"/goals/{gid}", headers=_h(token_a), json={"current_amount": "80"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


def test_patch_target_para_baixo_pode_marcar_completed(token_a: str) -> None:
    """Reduzir o target abaixo do current marca completed."""
    r = client.post(
        "/goals",
        headers=_h(token_a),
        json={"name": "X", "target_amount": "1000", "current_amount": "200"},
    )
    gid = r.json()["id"]
    assert r.json()["status"] == "in_progress"

    r = client.patch(f"/goals/{gid}", headers=_h(token_a), json={"target_amount": "150"})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_list_isola_por_usuario(token_a: str, token_b: str) -> None:
    client.post("/goals", headers=_h(token_a), json={"name": "Ag", "target_amount": "100"})
    client.post("/goals", headers=_h(token_b), json={"name": "Bg", "target_amount": "200"})
    r_a = client.get("/goals", headers=_h(token_a))
    assert [g["name"] for g in r_a.json()] == ["Ag"]
    r_b = client.get("/goals", headers=_h(token_b))
    assert [g["name"] for g in r_b.json()] == ["Bg"]


def test_get_patch_delete_404_para_outro(token_a: str, token_b: str) -> None:
    r = client.post("/goals", headers=_h(token_a), json={"name": "X", "target_amount": "1"})
    gid = r.json()["id"]
    assert client.get(f"/goals/{gid}", headers=_h(token_b)).status_code == 404
    assert client.patch(f"/goals/{gid}", headers=_h(token_b), json={"name": "h"}).status_code == 404
    assert client.delete(f"/goals/{gid}", headers=_h(token_b)).status_code == 404


def test_delete_204(token_a: str) -> None:
    r = client.post("/goals", headers=_h(token_a), json={"name": "X", "target_amount": "1"})
    gid = r.json()["id"]
    assert client.delete(f"/goals/{gid}", headers=_h(token_a)).status_code == 204
    assert client.get(f"/goals/{gid}", headers=_h(token_a)).status_code == 404


def test_payload_invalido_422(token_a: str) -> None:
    assert (
        client.post(
            "/goals",
            headers=_h(token_a),
            json={"name": "", "target_amount": "100"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/goals",
            headers=_h(token_a),
            json={"name": "X", "target_amount": "0"},
        ).status_code
        == 422
    )


def test_sem_token_401() -> None:
    assert client.get("/goals").status_code == 401
    assert client.post("/goals", json={"name": "X", "target_amount": "1"}).status_code == 401
