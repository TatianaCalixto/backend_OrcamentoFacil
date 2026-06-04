"""Testes do CRUD /transactions com filtros e paginacao (S05-T04)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.categories.models import Category
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register(email: str) -> tuple[str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"], user_id


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_account(token: str, name: str = "Conta") -> int:
    r = client.post(
        "/accounts",
        headers=_h(token),
        json={"name": name, "type": "checking", "initial_balance": "1000.00"},
    )
    return r.json()["id"]


async def _income_category(user_id: int) -> int:
    """Cria uma categoria income para o user (defaults sao todas expense)."""
    async with SessionLocal() as db:
        cat = Category(user_id=user_id, name="Salario", type="income")
        db.add(cat)
        await db.commit()
        return cat.id


def _expense_category_id(token: str) -> int:
    """Pega uma das categorias default (expense) do user."""
    r = client.get("/categories", headers=_h(token))
    return next(c["id"] for c in r.json() if c["type"] == "expense")


@pytest.fixture
async def setup_user_a():
    token, uid = _register("a@ex.com")
    acc = _create_account(token, "C1")
    cat_in = await _income_category(uid)
    cat_ex = _expense_category_id(token)
    return {"token": token, "uid": uid, "acc": acc, "cat_in": cat_in, "cat_ex": cat_ex}


@pytest.fixture
async def setup_user_b():
    token, uid = _register("b@ex.com")
    acc = _create_account(token, "B1")
    cat_in = await _income_category(uid)
    return {"token": token, "uid": uid, "acc": acc, "cat_in": cat_in}


# --------------------------- CRUD basico ---------------------------


def test_post_cria_transacao_e_201(setup_user_a) -> None:
    r = client.post(
        "/transactions",
        headers=_h(setup_user_a["token"]),
        json={
            "account_id": setup_user_a["acc"],
            "category_id": setup_user_a["cat_in"],
            "type": "income",
            "amount": "100.00",
            "date": "2026-05-23",
            "description": "Salario",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount"] == "100.00"
    # saldo da conta foi atualizado: 1000 + 100 = 1100
    r2 = client.get(f"/accounts/{setup_user_a['acc']}", headers=_h(setup_user_a["token"]))
    assert r2.json()["current_balance"] == "1100.00"


def test_post_com_account_de_outro_user_retorna_404(setup_user_a, setup_user_b) -> None:
    r = client.post(
        "/transactions",
        headers=_h(setup_user_a["token"]),
        json={
            "account_id": setup_user_b["acc"],
            "category_id": setup_user_a["cat_in"],
            "type": "income",
            "amount": "10.00",
            "date": "2026-05-23",
        },
    )
    assert r.status_code == 404


def test_get_by_id_e_404_se_de_outro(setup_user_a, setup_user_b) -> None:
    r = client.post(
        "/transactions",
        headers=_h(setup_user_a["token"]),
        json={
            "account_id": setup_user_a["acc"],
            "category_id": setup_user_a["cat_in"],
            "type": "income",
            "amount": "1",
            "date": "2026-05-23",
        },
    )
    tid = r.json()["id"]
    assert client.get(f"/transactions/{tid}", headers=_h(setup_user_a["token"])).status_code == 200
    assert client.get(f"/transactions/{tid}", headers=_h(setup_user_b["token"])).status_code == 404


def test_patch_e_delete_404_para_outro(setup_user_a, setup_user_b) -> None:
    r = client.post(
        "/transactions",
        headers=_h(setup_user_a["token"]),
        json={
            "account_id": setup_user_a["acc"],
            "category_id": setup_user_a["cat_in"],
            "type": "income",
            "amount": "1",
            "date": "2026-05-23",
        },
    )
    tid = r.json()["id"]
    assert (
        client.patch(
            f"/transactions/{tid}",
            headers=_h(setup_user_b["token"]),
            json={"amount": "9999"},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/transactions/{tid}", headers=_h(setup_user_b["token"])).status_code == 404
    )


def test_delete_remove_e_204(setup_user_a) -> None:
    r = client.post(
        "/transactions",
        headers=_h(setup_user_a["token"]),
        json={
            "account_id": setup_user_a["acc"],
            "category_id": setup_user_a["cat_ex"],
            "type": "expense",
            "amount": "50",
            "date": "2026-05-23",
        },
    )
    tid = r.json()["id"]
    r = client.delete(f"/transactions/{tid}", headers=_h(setup_user_a["token"]))
    assert r.status_code == 204
    assert client.get(f"/transactions/{tid}", headers=_h(setup_user_a["token"])).status_code == 404


# --------------------------- filtros e paginacao ---------------------------


def _seed_8(token: str, acc: int, cat_in: int, cat_ex: int) -> None:
    for _i, (amount, type_, dt, descr, cat) in enumerate(
        [
            ("100", "income", "2026-05-01", "Salario", cat_in),
            ("20", "expense", "2026-05-02", "Mercado", cat_ex),
            ("15", "expense", "2026-05-03", "Uber", cat_ex),
            ("80", "expense", "2026-05-04", "Restaurante", cat_ex),
            ("50", "income", "2026-05-05", "Freelance", cat_in),
            ("10", "expense", "2026-06-01", "Padaria", cat_ex),
            ("200", "income", "2026-06-02", "Bonus", cat_in),
            ("60", "expense", "2026-06-03", "Uber", cat_ex),
        ]
    ):
        r = client.post(
            "/transactions",
            headers=_h(token),
            json={
                "account_id": acc,
                "category_id": cat,
                "type": type_,
                "amount": amount,
                "date": dt,
                "description": descr,
            },
        )
        assert r.status_code == 201, r.text


def test_get_lista_paginada_com_metadados(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get("/transactions?page=1&page_size=3", headers=_h(setup_user_a["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 8
    assert body["page"] == 1
    assert body["page_size"] == 3
    assert len(body["items"]) == 3

    r = client.get("/transactions?page=3&page_size=3", headers=_h(setup_user_a["token"]))
    body = r.json()
    assert len(body["items"]) == 2  # 8 - 3 - 3 = 2


def test_filtro_date_range(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get(
        "/transactions?date_from=2026-06-01&date_to=2026-06-30&page_size=50",
        headers=_h(setup_user_a["token"]),
    )
    assert r.json()["total"] == 3  # 3 em junho


def test_filtro_type(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get("/transactions?type=expense&page_size=50", headers=_h(setup_user_a["token"]))
    assert r.json()["total"] == 5
    r = client.get("/transactions?type=income&page_size=50", headers=_h(setup_user_a["token"]))
    assert r.json()["total"] == 3


def test_filtro_search_case_insensitive(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get("/transactions?search=uber&page_size=50", headers=_h(setup_user_a["token"]))
    assert r.json()["total"] == 2
    r = client.get("/transactions?search=UBER&page_size=50", headers=_h(setup_user_a["token"]))
    assert r.json()["total"] == 2


def test_filtros_combinados(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get(
        "/transactions?type=expense&date_from=2026-06-01&page_size=50",
        headers=_h(setup_user_a["token"]),
    )
    assert r.json()["total"] == 2  # padaria + uber em junho


def test_isolamento_entre_users(setup_user_a, setup_user_b) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    # b cria a propria
    client.post(
        "/transactions",
        headers=_h(setup_user_b["token"]),
        json={
            "account_id": setup_user_b["acc"],
            "category_id": setup_user_b["cat_in"],
            "type": "income",
            "amount": "999",
            "date": "2026-05-23",
        },
    )
    r = client.get("/transactions?page_size=50", headers=_h(setup_user_a["token"]))
    assert r.json()["total"] == 8
    r = client.get("/transactions?page_size=50", headers=_h(setup_user_b["token"]))
    assert r.json()["total"] == 1


def test_order_by_amount_desc(setup_user_a) -> None:
    _seed_8(
        setup_user_a["token"], setup_user_a["acc"], setup_user_a["cat_in"], setup_user_a["cat_ex"]
    )
    r = client.get("/transactions?order_by=-amount&page_size=3", headers=_h(setup_user_a["token"]))
    amounts = [float(i["amount"]) for i in r.json()["items"]]
    assert amounts == sorted(amounts, reverse=True)


def test_sem_token_401() -> None:
    assert client.get("/transactions").status_code == 401
    assert (
        client.post(
            "/transactions",
            json={
                "account_id": 1,
                "category_id": 1,
                "type": "income",
                "amount": "10",
                "date": "2026-05-23",
            },
        ).status_code
        == 401
    )
