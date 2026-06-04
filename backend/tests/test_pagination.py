"""Paginacao opcional em /budgets e /goals (S24-T06).

A resposta continua sendo uma LISTA (sem quebrar clientes atuais); os
endpoints passam a aceitar page/page_size opcionais (page_size default 50).
Ordem: mais antigos primeiro (id ASC).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _auth(email: str) -> dict[str, str]:
    client.post("/auth/register", json={"name": "P", "email": email, "password": "Senha123"})
    r = client.post("/auth/login", json={"email": email, "password": "Senha123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_goals_paginacao_pagina_cheia_parcial_e_vazia() -> None:
    h = _auth("pag_goals@ex.com")
    ids = []
    for i in range(3):
        r = client.post("/goals", headers=h, json={"name": f"Meta {i}", "target_amount": "100.00"})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])

    # default (sem params): lista completa, mais antigos primeiro (compatibilidade)
    r = client.get("/goals", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert [g["id"] for g in r.json()] == ids

    # pagina cheia
    r = client.get("/goals?page=1&page_size=2", headers=h)
    assert [g["id"] for g in r.json()] == ids[:2]

    # pagina parcial (resto)
    r = client.get("/goals?page=2&page_size=2", headers=h)
    assert [g["id"] for g in r.json()] == ids[2:]

    # pagina vazia (alem do fim)
    r = client.get("/goals?page=3&page_size=2", headers=h)
    assert r.json() == []


def test_budgets_paginacao_pagina_cheia_parcial_e_vazia() -> None:
    h = _auth("pag_budgets@ex.com")
    cats = [c["id"] for c in client.get("/categories", headers=h).json()][:3]
    assert len(cats) == 3

    ids = []
    for cid in cats:
        r = client.post(
            "/budgets",
            headers=h,
            json={"category_id": cid, "month": 5, "year": 2026, "limit_amount": "100.00"},
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])

    # default (mes/ano informados, sem page): lista completa, mais antigos primeiro
    r = client.get("/budgets?month=5&year=2026", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert [b["id"] for b in r.json()] == ids

    # pagina cheia
    r = client.get("/budgets?month=5&year=2026&page=1&page_size=2", headers=h)
    assert [b["id"] for b in r.json()] == ids[:2]

    # pagina parcial (resto)
    r = client.get("/budgets?month=5&year=2026&page=2&page_size=2", headers=h)
    assert [b["id"] for b in r.json()] == ids[2:]

    # pagina vazia (alem do fim)
    r = client.get("/budgets?month=5&year=2026&page=3&page_size=2", headers=h)
    assert r.json() == []


def test_paginacao_default_page_size_50_retorna_tudo_para_listas_pequenas() -> None:
    """Sem page/page_size, o default 50 cobre os casos reais (lista completa)."""
    h = _auth("pag_default@ex.com")
    for i in range(5):
        client.post("/goals", headers=h, json={"name": f"M{i}", "target_amount": "10.00"})
    r = client.get("/goals", headers=h)
    assert len(r.json()) == 5
