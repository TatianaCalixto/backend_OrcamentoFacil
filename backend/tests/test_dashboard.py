"""Testes do Dashboard (Sprint 8: S08-T01, T02, T03)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.categories.models import Category
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register(email: str) -> tuple[str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"], uid


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_acc(token: str, name: str, initial: str = "0") -> int:
    r = client.post(
        "/accounts",
        headers=_h(token),
        json={"name": name, "type": "checking", "initial_balance": initial},
    )
    return r.json()["id"]


def _income_cat(uid: int, name: str) -> int:
    with SessionLocal() as db:
        c = Category(user_id=uid, name=name, type="income")
        db.add(c)
        db.commit()
        return c.id


def _expense_cat(token: str) -> int:
    r = client.get("/categories", headers=_h(token))
    return next(c["id"] for c in r.json() if c["type"] == "expense")


def _tx(token: str, acc: int, cat: int, type_: str, amount: str, dt: str) -> None:
    r = client.post(
        "/transactions",
        headers=_h(token),
        json={
            "account_id": acc,
            "category_id": cat,
            "type": type_,
            "amount": amount,
            "date": dt,
        },
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def setup_a():
    token, uid = _register("a@ex.com")
    acc1 = _create_acc(token, "Nu", "1000")
    acc2 = _create_acc(token, "Poup", "500")
    cat_in = _income_cat(uid, "Salario")
    cat_ex = _expense_cat(token)
    return {
        "token": token,
        "uid": uid,
        "acc1": acc1,
        "acc2": acc2,
        "cat_in": cat_in,
        "cat_ex": cat_ex,
    }


# ===================== monthly-summary =====================


def test_summary_mes_vazio_retorna_zeros(setup_a) -> None:
    r = client.get("/dashboard/monthly-summary?month=5&year=2026", headers=_h(setup_a["token"]))
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["receita_total"]) == Decimal("0")
    assert Decimal(body["despesa_total"]) == Decimal("0")
    assert Decimal(body["saldo"]) == Decimal("0")
    assert len(body["contas"]) == 2


def test_summary_com_transacoes(setup_a) -> None:
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "1000.00", "2026-05-10")
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_ex"], "expense", "300.00", "2026-05-15")
    _tx(setup_a["token"], setup_a["acc2"], setup_a["cat_in"], "income", "500.00", "2026-05-20")
    # transacao fora do mes nao conta
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "9999.00", "2026-04-30")

    r = client.get("/dashboard/monthly-summary?month=5&year=2026", headers=_h(setup_a["token"]))
    body = r.json()
    assert body["receita_total"] == "1500.00"
    assert body["despesa_total"] == "300.00"
    assert body["saldo"] == "1200.00"
    # contas mostram current_balance atual (afetado por TODAS as txns, mesmo fora do mes)
    assert {c["name"] for c in body["contas"]} == {"Nu", "Poup"}


def test_summary_isolamento_entre_users(setup_a) -> None:
    token_b, _uid_b = _register("b@ex.com")
    _create_acc(token_b, "Bcc")

    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "100.00", "2026-05-10")

    r = client.get("/dashboard/monthly-summary?month=5&year=2026", headers=_h(token_b))
    body = r.json()
    assert Decimal(body["receita_total"]) == Decimal("0")
    assert len(body["contas"]) == 1


# ===================== category-breakdown =====================


def test_breakdown_mes_vazio_lista_vazia(setup_a) -> None:
    r = client.get("/dashboard/category-breakdown?month=5&year=2026", headers=_h(setup_a["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []


def test_breakdown_ordenado_desc_e_so_despesas(setup_a) -> None:
    # cria mais uma categoria expense
    with SessionLocal() as db:
        outra = Category(user_id=setup_a["uid"], name="Lazer", type="expense")
        db.add(outra)
        db.commit()
        outra_id = outra.id

    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_ex"], "expense", "100", "2026-05-01")
    _tx(setup_a["token"], setup_a["acc1"], outra_id, "expense", "300", "2026-05-02")
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_ex"], "expense", "50", "2026-05-03")
    # receita NAO conta no breakdown
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "9999", "2026-05-04")

    r = client.get("/dashboard/category-breakdown?month=5&year=2026", headers=_h(setup_a["token"]))
    body = r.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "Lazer"
    assert Decimal(body["items"][0]["total"]) == Decimal("300")
    assert Decimal(body["items"][1]["total"]) == Decimal("150")  # 100 + 50


# ===================== cashflow =====================


def test_cashflow_periodo_curto_3_dias(setup_a) -> None:
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "100", "2026-05-01")
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_ex"], "expense", "30", "2026-05-02")
    _tx(setup_a["token"], setup_a["acc1"], setup_a["cat_in"], "income", "50", "2026-05-03")

    r = client.get(
        "/dashboard/cashflow?date_from=2026-05-01&date_to=2026-05-03",
        headers=_h(setup_a["token"]),
    )
    body = r.json()
    pts = body["points"]
    assert len(pts) == 3
    # ordem por data
    assert [p["date"] for p in pts] == ["2026-05-01", "2026-05-02", "2026-05-03"]
    # saldos acumulados: 100, 70, 120
    assert [Decimal(p["saldo_acumulado"]) for p in pts] == [
        Decimal("100"),
        Decimal("70"),
        Decimal("120"),
    ]


def test_cashflow_periodo_sem_dados_vazio(setup_a) -> None:
    r = client.get(
        "/dashboard/cashflow?date_from=2030-01-01&date_to=2030-01-31",
        headers=_h(setup_a["token"]),
    )
    body = r.json()
    assert body["points"] == []


def test_cashflow_longo_30_dias(setup_a) -> None:
    """Cria 30 transacoes em dias distintos e valida ordem + acumulado."""
    for d in range(1, 31):
        _tx(
            setup_a["token"],
            setup_a["acc1"],
            setup_a["cat_in"],
            "income",
            "10.00",
            date(2026, 5, d).isoformat(),
        )
    r = client.get(
        "/dashboard/cashflow?date_from=2026-05-01&date_to=2026-05-31",
        headers=_h(setup_a["token"]),
    )
    pts = r.json()["points"]
    assert len(pts) == 30
    # ultimo acumulado = 30 * 10 = 300
    assert pts[-1]["saldo_acumulado"] == "300.00"


# ===================== auth =====================


def test_dashboard_sem_token_401() -> None:
    assert client.get("/dashboard/monthly-summary").status_code == 401
    assert client.get("/dashboard/category-breakdown").status_code == 401
    assert (
        client.get("/dashboard/cashflow?date_from=2026-01-01&date_to=2026-12-31").status_code == 401
    )
