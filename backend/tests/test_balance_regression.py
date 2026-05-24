"""Bateria de regressao de saldo (S05-T05) — CRITICO.

Estes testes formam a guarda permanente da regra de saldo:
- Criar transacao atualiza current_balance.
- Editar (amount, type, account) atualiza corretamente em ambas contas.
- Deletar reverte.

QUEBROU? PARE TUDO e investigue antes de prosseguir com a sprint corrente.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.categories.models import Category
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register_login(email: str) -> tuple[str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    return r.json()["access_token"], uid


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _balance(token: str, account_id: int) -> Decimal:
    r = client.get(f"/accounts/{account_id}", headers=_h(token))
    assert r.status_code == 200
    return Decimal(r.json()["current_balance"])


def _create_account(token: str, name: str, initial: str) -> int:
    r = client.post(
        "/accounts",
        headers=_h(token),
        json={"name": name, "type": "checking", "initial_balance": initial},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _income_cat(uid: int, name: str) -> int:
    with SessionLocal() as db:
        c = Category(user_id=uid, name=name, type="income")
        db.add(c)
        db.commit()
        return c.id


def _expense_cat_id(token: str) -> int:
    r = client.get("/categories", headers=_h(token))
    return next(c["id"] for c in r.json() if c["type"] == "expense")


def _post_tx(
    token: str,
    *,
    account_id: int,
    category_id: int,
    type_: str,
    amount: str,
    dt: str = "2026-05-23",
    description: str = "",
) -> int:
    r = client.post(
        "/transactions",
        headers=_h(token),
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": type_,
            "amount": amount,
            "date": dt,
            "description": description,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _patch_tx(token: str, tid: int, **patch) -> None:
    # traduz aliases dos kwargs para os nomes reais do schema
    if "type_" in patch:
        patch["type"] = patch.pop("type_")
    if "dt" in patch:
        patch["date"] = patch.pop("dt")
    r = client.patch(f"/transactions/{tid}", headers=_h(token), json=patch)
    assert r.status_code == 200, r.text


def _delete_tx(token: str, tid: int) -> None:
    r = client.delete(f"/transactions/{tid}", headers=_h(token))
    assert r.status_code == 204


# ============================================================
# TESTE PRINCIPAL — fluxo realista longo
# ============================================================


def test_balance_regression_full_flow() -> None:
    """Fluxo realista: 2 contas, varias transacoes, edicoes, mudancas de
    conta e deletes. Saldos finais conferem ao centavo."""
    token, uid = _register_login("ana@ex.com")

    # contas iniciais
    nubank = _create_account(token, "Nubank", "1000.00")
    poup = _create_account(token, "Poupanca", "5000.00")

    # categorias
    salario = _income_cat(uid, "Salario")
    despesa = _expense_cat_id(token)  # categoria default expense

    # ---- semana 1: salario + algumas despesas ----
    t1 = _post_tx(
        token,
        account_id=nubank,
        category_id=salario,
        type_="income",
        amount="3500.00",
        dt="2026-05-01",
        description="Salario maio",
    )
    _post_tx(
        token,
        account_id=nubank,
        category_id=despesa,
        type_="expense",
        amount="450.00",
        dt="2026-05-02",
        description="Mercado",
    )
    _post_tx(
        token,
        account_id=nubank,
        category_id=despesa,
        type_="expense",
        amount="80.00",
        dt="2026-05-03",
        description="Padaria",
    )
    _post_tx(
        token,
        account_id=nubank,
        category_id=despesa,
        type_="expense",
        amount="120.00",
        dt="2026-05-04",
        description="Uber",
    )

    # nubank: 1000 + 3500 - 450 - 80 - 120 = 3850
    assert _balance(token, nubank) == Decimal("3850.00")
    assert _balance(token, poup) == Decimal("5000.00")

    # ---- transferencia simulada via 2 lancamentos (poupanca recebe) ----
    # 1) despesa em nubank de 500 (transferencia para poupanca)
    t_out = _post_tx(
        token,
        account_id=nubank,
        category_id=despesa,
        type_="expense",
        amount="500.00",
        dt="2026-05-05",
        description="Transf para poupanca",
    )
    # 2) receita em poupanca de 500
    t_in = _post_tx(
        token,
        account_id=poup,
        category_id=salario,
        type_="income",
        amount="500.00",
        dt="2026-05-05",
        description="Vindo de Nubank",
    )

    # nubank: 3850 - 500 = 3350; poup: 5000 + 500 = 5500
    assert _balance(token, nubank) == Decimal("3350.00")
    assert _balance(token, poup) == Decimal("5500.00")

    # ---- editar: corrigir valor da padaria de 80 para 75 ----
    # achar t da padaria pelo search
    r = client.get("/transactions?search=Padaria", headers=_h(token))
    tid_padaria = r.json()["items"][0]["id"]
    _patch_tx(token, tid_padaria, amount="75.00")
    # nubank: 3350 + (75 - 80) erro: delta = -75 - (-80) = +5; entao 3350 + 5 = 3355
    assert _balance(token, nubank) == Decimal("3355.00")

    # ---- editar: o salario era 3500 mas vai virar 3700 ----
    _patch_tx(token, t1, amount="3700.00")
    # delta = +3700 - (+3500) = +200; nubank: 3355 + 200 = 3555
    assert _balance(token, nubank) == Decimal("3555.00")

    # ---- editar: mudar t_out de tipo expense -> income (fica como devolucao) ----
    _patch_tx(token, t_out, type_="income")
    # delta = +500 - (-500) = +1000; nubank: 3555 + 1000 = 4555
    assert _balance(token, nubank) == Decimal("4555.00")

    # ---- editar: mudar t_in para nubank em vez de poupanca, e tipo expense, e valor 100 ----
    _patch_tx(token, t_in, account_id=nubank, type_="expense", amount="100.00")
    # poup: reverte +500 (era income na poup) -> -500; 5500 - 500 = 5000
    # nubank: aplica -100; 4555 - 100 = 4455
    assert _balance(token, poup) == Decimal("5000.00")
    assert _balance(token, nubank) == Decimal("4455.00")

    # ---- deletar t1 (salario) ----
    _delete_tx(token, t1)
    # nubank: reverte +3700; 4455 - 3700 = 755
    assert _balance(token, nubank) == Decimal("755.00")

    # ---- inserir 5 transacoes pequenas e validar soma ----
    for amount, type_ in [
        ("10.50", "expense"),
        ("20.00", "income"),
        ("30.25", "expense"),
        ("40.75", "income"),
        ("50.00", "expense"),
    ]:
        cat = salario if type_ == "income" else despesa
        _post_tx(
            token, account_id=nubank, category_id=cat, type_=type_, amount=amount, dt="2026-05-10"
        )
    # delta: -10.50 + 20 - 30.25 + 40.75 - 50 = -30
    assert _balance(token, nubank) == Decimal("725.00")  # 755 - 30

    # ---- limpar TODAS as transacoes do user e validar volta aos initial_balance ----
    r = client.get("/transactions?page_size=100", headers=_h(token))
    txn_ids = [t["id"] for t in r.json()["items"]]
    for tid in txn_ids:
        _delete_tx(token, tid)

    # zero transacoes, saldos voltam ao initial_balance
    assert _balance(token, nubank) == Decimal("1000.00")
    assert _balance(token, poup) == Decimal("5000.00")


# ============================================================
# Testes adicionais (regressao curta de propriedades-chave)
# ============================================================


def test_balance_regression_soma_de_lista_eh_consistente() -> None:
    """Para qualquer sequencia de N transacoes em uma conta zerada,
    current_balance == sum(income) - sum(expense)."""
    token, uid = _register_login("a@ex.com")
    acc = _create_account(token, "X", "0.00")
    income_cat = _income_cat(uid, "I")
    expense_cat = _expense_cat_id(token)

    operacoes = [
        ("income", "123.45"),
        ("expense", "67.89"),
        ("income", "1000.00"),
        ("expense", "999.99"),
        ("income", "0.01"),
        ("expense", "0.02"),
        ("income", "555.55"),
        ("expense", "111.11"),
    ]
    for type_, amount in operacoes:
        cat = income_cat if type_ == "income" else expense_cat
        _post_tx(token, account_id=acc, category_id=cat, type_=type_, amount=amount)

    esperado = sum(Decimal(a) if t == "income" else -Decimal(a) for t, a in operacoes)
    assert _balance(token, acc) == esperado


def test_balance_regression_initial_balance_eh_imutavel_via_api() -> None:
    """A regra atual: current_balance varia; initial_balance NAO muda quando
    se cria transacoes. (Documenta invariante; a edicao manual de
    initial_balance via PATCH /accounts nao esta no contrato desta sprint.)"""
    token, uid = _register_login("a@ex.com")
    acc = _create_account(token, "X", "500.00")
    cat_in = _income_cat(uid, "I")

    _post_tx(token, account_id=acc, category_id=cat_in, type_="income", amount="100")

    r = client.get(f"/accounts/{acc}", headers=_h(token))
    body = r.json()
    assert body["initial_balance"] == "500.00"
    assert body["current_balance"] == "600.00"


@pytest.mark.parametrize(
    ("ops", "esperado_str"),
    [
        ([("income", "100"), ("expense", "30"), ("income", "50")], "120.00"),
        ([("expense", "100")], "-100.00"),
        ([("income", "0.01"), ("income", "0.02"), ("income", "0.03")], "0.06"),
    ],
)
def test_balance_regression_parametrico_pequenos_casos(ops, esperado_str) -> None:
    token, uid = _register_login("x@ex.com")
    acc = _create_account(token, "X", "0.00")
    cat_in = _income_cat(uid, "I")
    cat_ex = _expense_cat_id(token)
    for type_, amount in ops:
        cat = cat_in if type_ == "income" else cat_ex
        _post_tx(token, account_id=acc, category_id=cat, type_=type_, amount=amount)
    assert _balance(token, acc) == Decimal(esperado_str)


def test_balance_regression_delete_apos_update_volta_ao_baseline() -> None:
    """Cria, edita varias vezes, deleta — saldo volta ao initial_balance."""
    token, uid = _register_login("y@ex.com")
    acc = _create_account(token, "X", "1000.00")
    cat_in = _income_cat(uid, "I")

    tid = _post_tx(token, account_id=acc, category_id=cat_in, type_="income", amount="100")
    _patch_tx(token, tid, amount="300")
    _patch_tx(token, tid, type_="expense")
    _patch_tx(token, tid, amount="50")
    _delete_tx(token, tid)

    assert _balance(token, acc) == Decimal("1000.00")


def test_balance_regression_e_isolada_entre_usuarios() -> None:
    """Transacoes do user A NUNCA podem mexer no saldo do user B."""
    token_a, uid_a = _register_login("a@ex.com")
    token_b, _uid_b = _register_login("b@ex.com")

    acc_a = _create_account(token_a, "Aca", "100.00")
    acc_b = _create_account(token_b, "Bca", "200.00")
    cat_a = _income_cat(uid_a, "Ia")

    # A cria varias transacoes
    for _ in range(5):
        _post_tx(token_a, account_id=acc_a, category_id=cat_a, type_="income", amount="10")

    # saldo de A muda, saldo de B nao
    assert _balance(token_a, acc_a) == Decimal("150.00")  # 100 + 5*10
    assert _balance(token_b, acc_b) == Decimal("200.00")  # intacto
