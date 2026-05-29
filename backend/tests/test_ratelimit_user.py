"""Rate limit por usuario nas mutacoes (S20-T03).

Limites: /imports/csv 1/min; /transactions POST/PATCH/DELETE 60/min;
/accounts POST/PATCH/DELETE 10/min; /budgets POST/PATCH 10/min;
/goals POST/PATCH/DELETE 10/min. Chave por usuario autenticado (user_or_ip_key).

O limiter fica desabilitado por padrao nos testes (conftest); aqui ligamos via
a fixture rate_limit_active. Para transactions/budgets usamos payloads
schema-validos com FK inexistente: chegam ao handler (404), entao o slowapi
conta a requisicao, sem precisar criar contas/categorias reais.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import limiter
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


def _has_retry_after(resp) -> bool:
    return "retry-after" in {k.lower() for k in resp.headers}


ACCOUNT = {"name": "C", "type": "checking", "initial_balance": "0.00"}
TXN = {
    "account_id": 999999,
    "category_id": 999999,
    "type": "expense",
    "amount": "10.00",
    "date": "2026-01-01",
}
BUDGET = {"category_id": 999999, "month": 1, "year": 2026, "limit_amount": "100.00"}
GOAL = {"name": "G", "target_amount": "100.00"}


def test_imports_csv_limite_1_por_min(rate_limit_active) -> None:
    token = _register_and_login("imp@ex.com")
    files = {"file": ("x.csv", b"data,descricao,valor\n", "text/csv")}
    r1 = client.post("/imports/csv", headers=_h(token), data={"account_id": "999999"}, files=files)
    assert r1.status_code != 429  # 1a chamada passa pelo limite (handler roda)
    files = {"file": ("x.csv", b"data,descricao,valor\n", "text/csv")}
    r2 = client.post("/imports/csv", headers=_h(token), data={"account_id": "999999"}, files=files)
    assert r2.status_code == 429
    assert _has_retry_after(r2)


def test_accounts_mutacoes_limite_10_por_min(rate_limit_active) -> None:
    token = _register_and_login("acc@ex.com")
    for _ in range(10):
        r = client.post("/accounts", headers=_h(token), json=ACCOUNT)
        assert r.status_code == 201, r.text
    r = client.post("/accounts", headers=_h(token), json=ACCOUNT)
    assert r.status_code == 429
    assert _has_retry_after(r)


def test_transactions_post_limite_60_por_min(rate_limit_active) -> None:
    token = _register_and_login("txn@ex.com")
    for _ in range(60):
        r = client.post("/transactions", headers=_h(token), json=TXN)
        assert r.status_code != 429  # 404 (FK inexistente), mas conta no limite
    r = client.post("/transactions", headers=_h(token), json=TXN)
    assert r.status_code == 429


def test_budgets_limite_10_por_min(rate_limit_active) -> None:
    token = _register_and_login("bud@ex.com")
    for _ in range(10):
        r = client.post("/budgets", headers=_h(token), json=BUDGET)
        assert r.status_code != 429
    r = client.post("/budgets", headers=_h(token), json=BUDGET)
    assert r.status_code == 429


def test_goals_limite_10_por_min(rate_limit_active) -> None:
    token = _register_and_login("goal@ex.com")
    for _ in range(10):
        r = client.post("/goals", headers=_h(token), json=GOAL)
        assert r.status_code == 201, r.text
    r = client.post("/goals", headers=_h(token), json=GOAL)
    assert r.status_code == 429


def test_get_nao_e_afetado(rate_limit_active) -> None:
    token = _register_and_login("get@ex.com")
    for _ in range(10):
        client.post("/accounts", headers=_h(token), json=ACCOUNT)
    assert client.post("/accounts", headers=_h(token), json=ACCOUNT).status_code == 429
    # GET continua livre mesmo com o POST estourado
    for _ in range(15):
        assert client.get("/accounts", headers=_h(token)).status_code == 200


def test_limite_e_por_usuario(rate_limit_active) -> None:
    token_a = _register_and_login("ua@ex.com", "A")
    token_b = _register_and_login("ub@ex.com", "B")
    for _ in range(10):
        client.post("/accounts", headers=_h(token_a), json=ACCOUNT)
    assert client.post("/accounts", headers=_h(token_a), json=ACCOUNT).status_code == 429
    # usuario B tem balde proprio
    assert client.post("/accounts", headers=_h(token_b), json=ACCOUNT).status_code == 201


def test_limite_reseta_apos_janela(rate_limit_active) -> None:
    token = _register_and_login("reset@ex.com")
    for _ in range(10):
        client.post("/accounts", headers=_h(token), json=ACCOUNT)
    assert client.post("/accounts", headers=_h(token), json=ACCOUNT).status_code == 429
    limiter.reset()  # simula a passagem da janela de tempo
    assert client.post("/accounts", headers=_h(token), json=ACCOUNT).status_code == 201
