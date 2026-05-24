"""Testes do CRUD /budgets (S06-T03)."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register(email: str) -> tuple[str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"], uid


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _expense_cat(token: str) -> int:
    r = client.get("/categories", headers=_h(token))
    return next(c["id"] for c in r.json() if c["type"] == "expense")


def _create_account(token: str) -> int:
    r = client.post(
        "/accounts",
        headers=_h(token),
        json={"name": "C", "type": "checking", "initial_balance": "1000"},
    )
    return r.json()["id"]


@pytest.fixture
def setup_a():
    token, uid = _register("a@ex.com")
    cat = _expense_cat(token)
    acc = _create_account(token)
    return {"token": token, "uid": uid, "cat": cat, "acc": acc}


@pytest.fixture
def setup_b():
    token, uid = _register("b@ex.com")
    cat = _expense_cat(token)
    return {"token": token, "uid": uid, "cat": cat}


def test_post_cria_budget(setup_a) -> None:
    r = client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": 5,
            "year": 2026,
            "limit_amount": "500.00",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["limit_amount"] == "500.00"


def test_post_com_category_de_outro_user_404(setup_a, setup_b) -> None:
    r = client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_b["cat"],
            "month": 5,
            "year": 2026,
            "limit_amount": "100",
        },
    )
    assert r.status_code == 404


def test_list_mes_corrente_calcula_status(setup_a) -> None:
    today = date.today()
    client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": today.month,
            "year": today.year,
            "limit_amount": "200.00",
        },
    )
    # cria uma despesa de hoje na categoria do budget
    client.post(
        "/transactions",
        headers=_h(setup_a["token"]),
        json={
            "account_id": setup_a["acc"],
            "category_id": setup_a["cat"],
            "type": "expense",
            "amount": "50.00",
            "date": today.isoformat(),
        },
    )
    r = client.get("/budgets", headers=_h(setup_a["token"]))
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    b = body[0]
    assert b["used_amount"] == "50.00"
    assert b["percent_used"] == "25.00"
    assert b["status"] == "ok"


def test_list_mes_passado_via_query(setup_a) -> None:
    client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": 1,
            "year": 2026,
            "limit_amount": "100",
        },
    )
    # default = mes corrente -> nao retorna o de jan/2026 (a nao ser que estejamos lah)
    r = client.get("/budgets?month=1&year=2026", headers=_h(setup_a["token"]))
    assert len(r.json()) == 1
    # mes diferente nao tem nada
    r = client.get("/budgets?month=2&year=2026", headers=_h(setup_a["token"]))
    assert len(r.json()) == 0


def test_patch_altera_limit(setup_a) -> None:
    r = client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": 5,
            "year": 2026,
            "limit_amount": "100",
        },
    )
    bid = r.json()["id"]
    r = client.patch(
        f"/budgets/{bid}",
        headers=_h(setup_a["token"]),
        json={"limit_amount": "999.00"},
    )
    assert r.status_code == 200
    assert r.json()["limit_amount"] == "999.00"


def test_get_by_id_404_para_outro(setup_a, setup_b) -> None:
    r = client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": 5,
            "year": 2026,
            "limit_amount": "100",
        },
    )
    bid = r.json()["id"]
    assert client.get(f"/budgets/{bid}", headers=_h(setup_a["token"])).status_code == 200
    assert client.get(f"/budgets/{bid}", headers=_h(setup_b["token"])).status_code == 404


def test_isolamento_no_list(setup_a, setup_b) -> None:
    client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={"category_id": setup_a["cat"], "month": 5, "year": 2026, "limit_amount": "100"},
    )
    client.post(
        "/budgets",
        headers=_h(setup_b["token"]),
        json={"category_id": setup_b["cat"], "month": 5, "year": 2026, "limit_amount": "200"},
    )
    r_a = client.get("/budgets?month=5&year=2026", headers=_h(setup_a["token"]))
    r_b = client.get("/budgets?month=5&year=2026", headers=_h(setup_b["token"]))
    assert len(r_a.json()) == 1
    assert len(r_b.json()) == 1
    assert r_a.json()[0]["limit_amount"] == "100.00"
    assert r_b.json()[0]["limit_amount"] == "200.00"


def test_payload_invalido_422(setup_a) -> None:
    r = client.post(
        "/budgets",
        headers=_h(setup_a["token"]),
        json={
            "category_id": setup_a["cat"],
            "month": 13,
            "year": 2026,
            "limit_amount": "100",
        },
    )
    assert r.status_code == 422


def test_sem_token_401() -> None:
    assert client.get("/budgets").status_code == 401
    assert (
        client.post(
            "/budgets", json={"category_id": 1, "month": 1, "year": 2026, "limit_amount": "1"}
        ).status_code
        == 401
    )
    assert client.patch("/budgets/1", json={"limit_amount": "1"}).status_code == 401
