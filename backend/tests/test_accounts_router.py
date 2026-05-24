"""Testes do CRUD /accounts (S03-T04). Foco: integracao + isolamento."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register_and_login(email: str, name: str = "User") -> str:
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token_a() -> str:
    return _register_and_login("a@ex.com", "Alice")


@pytest.fixture
def token_b() -> str:
    return _register_and_login("b@ex.com", "Bob")


# ------------------------- felizes -------------------------


def test_post_cria_conta_e_retorna_201(token_a: str) -> None:
    r = client.post(
        "/accounts",
        headers=_h(token_a),
        json={"name": "Nubank", "type": "checking", "initial_balance": "150.00"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Nubank"
    assert body["type"] == "checking"
    assert body["initial_balance"] == "150.00"
    assert body["current_balance"] == "150.00"  # regra de inicio
    assert body["is_active"] is True


def test_get_lista_so_retorna_minhas_contas(token_a: str, token_b: str) -> None:
    client.post(
        "/accounts",
        headers=_h(token_a),
        json={"name": "A1", "type": "cash"},
    )
    client.post(
        "/accounts",
        headers=_h(token_b),
        json={"name": "B1", "type": "cash"},
    )
    r = client.get("/accounts", headers=_h(token_a))
    assert r.status_code == 200
    nomes = [a["name"] for a in r.json()]
    assert nomes == ["A1"]


def test_get_by_id_feliz(token_a: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "X", "type": "cash"})
    aid = r.json()["id"]
    r = client.get(f"/accounts/{aid}", headers=_h(token_a))
    assert r.status_code == 200
    assert r.json()["id"] == aid


def test_patch_atualiza_campos_parciais(token_a: str) -> None:
    r = client.post(
        "/accounts",
        headers=_h(token_a),
        json={"name": "Old", "type": "checking"},
    )
    aid = r.json()["id"]
    r = client.patch(
        f"/accounts/{aid}",
        headers=_h(token_a),
        json={"name": "New", "is_active": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "New"
    assert body["is_active"] is False
    assert body["type"] == "checking"


def test_delete_remove_e_204(token_a: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "X", "type": "cash"})
    aid = r.json()["id"]
    r = client.delete(f"/accounts/{aid}", headers=_h(token_a))
    assert r.status_code == 204
    r = client.get(f"/accounts/{aid}", headers=_h(token_a))
    assert r.status_code == 404


# ------------------------- isolamento entre usuarios -------------------------


def test_user_b_nao_le_conta_do_user_a(token_a: str, token_b: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "X", "type": "cash"})
    aid = r.json()["id"]
    r = client.get(f"/accounts/{aid}", headers=_h(token_b))
    assert r.status_code == 404


def test_user_b_nao_edita_conta_do_user_a(token_a: str, token_b: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "X", "type": "cash"})
    aid = r.json()["id"]
    r = client.patch(f"/accounts/{aid}", headers=_h(token_b), json={"name": "hack"})
    assert r.status_code == 404


def test_user_b_nao_deleta_conta_do_user_a(token_a: str, token_b: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "X", "type": "cash"})
    aid = r.json()["id"]
    r = client.delete(f"/accounts/{aid}", headers=_h(token_b))
    assert r.status_code == 404
    # confirma que conta ainda existe para A
    r = client.get(f"/accounts/{aid}", headers=_h(token_a))
    assert r.status_code == 200


# ------------------------- guardas de auth -------------------------


def test_sem_token_retorna_401() -> None:
    assert client.get("/accounts").status_code == 401
    assert client.post("/accounts", json={"name": "X", "type": "cash"}).status_code == 401
    assert client.get("/accounts/1").status_code == 401
    assert client.patch("/accounts/1", json={"name": "Y"}).status_code == 401
    assert client.delete("/accounts/1").status_code == 401


def test_payload_invalido_em_post_retorna_422(token_a: str) -> None:
    r = client.post("/accounts", headers=_h(token_a), json={"name": "", "type": "bitcoin"})
    assert r.status_code == 422


def test_conta_inexistente_retorna_404(token_a: str) -> None:
    assert client.get("/accounts/9999", headers=_h(token_a)).status_code == 404
    assert (
        client.patch("/accounts/9999", headers=_h(token_a), json={"name": "X"}).status_code == 404
    )
    assert client.delete("/accounts/9999", headers=_h(token_a)).status_code == 404
