"""Testes do CRUD /categories (S04-T03)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register_and_login(email: str) -> str:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token_a() -> str:
    return _register_and_login("a@ex.com")


@pytest.fixture
def token_b() -> str:
    return _register_and_login("b@ex.com")


def test_list_apos_register_traz_8_defaults(token_a: str) -> None:
    r = client.get("/categories", headers=_h(token_a))
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 8
    assert all(c["is_default"] is True for c in cats)


def test_post_cria_categoria_custom_com_cor_e_icone(token_a: str) -> None:
    r = client.post(
        "/categories",
        headers=_h(token_a),
        json={
            "name": "Pet shop",
            "type": "expense",
            "color": "#FF00AA",
            "icon": "dog",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Pet shop"
    assert body["type"] == "expense"
    assert body["color"] == "#ff00aa"  # normalizado para lower
    assert body["icon"] == "dog"
    assert body["is_default"] is False


def test_post_color_invalido_422(token_a: str) -> None:
    r = client.post(
        "/categories",
        headers=_h(token_a),
        json={"name": "X", "type": "expense", "color": "vermelho"},
    )
    assert r.status_code == 422


def test_patch_atualiza_parcial(token_a: str) -> None:
    # cria uma custom
    r = client.post(
        "/categories",
        headers=_h(token_a),
        json={"name": "X", "type": "expense"},
    )
    cid = r.json()["id"]

    r = client.patch(
        f"/categories/{cid}",
        headers=_h(token_a),
        json={"icon": "star", "color": "#abcdef"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["icon"] == "star"
    assert body["color"] == "#abcdef"
    assert body["name"] == "X"


def test_delete_204(token_a: str) -> None:
    r = client.post("/categories", headers=_h(token_a), json={"name": "Tmp", "type": "expense"})
    cid = r.json()["id"]
    r = client.delete(f"/categories/{cid}", headers=_h(token_a))
    assert r.status_code == 204
    r = client.get(f"/categories/{cid}", headers=_h(token_a))
    assert r.status_code == 404


def test_isolamento_entre_usuarios(token_a: str, token_b: str) -> None:
    r = client.post("/categories", headers=_h(token_a), json={"name": "Z", "type": "expense"})
    cid = r.json()["id"]
    assert client.get(f"/categories/{cid}", headers=_h(token_b)).status_code == 404
    assert (
        client.patch(f"/categories/{cid}", headers=_h(token_b), json={"name": "hack"}).status_code
        == 404
    )
    assert client.delete(f"/categories/{cid}", headers=_h(token_b)).status_code == 404
    assert client.get(f"/categories/{cid}", headers=_h(token_a)).status_code == 200


def test_sem_token_401() -> None:
    assert client.get("/categories").status_code == 401
    assert client.post("/categories", json={"name": "X", "type": "expense"}).status_code == 401
    assert client.get("/categories/1").status_code == 401
    assert client.patch("/categories/1", json={"name": "X"}).status_code == 401
    assert client.delete("/categories/1").status_code == 401


def test_categoria_inexistente_404(token_a: str) -> None:
    assert client.get("/categories/9999", headers=_h(token_a)).status_code == 404
    assert (
        client.patch("/categories/9999", headers=_h(token_a), json={"name": "X"}).status_code == 404
    )
    assert client.delete("/categories/9999", headers=_h(token_a)).status_code == 404
