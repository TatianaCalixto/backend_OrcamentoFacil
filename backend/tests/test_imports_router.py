"""Testes do endpoint POST /imports/csv (S09-T01 e S09-T03)."""

from __future__ import annotations

import io
from decimal import Decimal

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


def _create_acc(token: str, initial: str = "1000.00") -> int:
    r = client.post(
        "/accounts",
        headers=_h(token),
        json={"name": "Nu", "type": "checking", "initial_balance": initial},
    )
    return r.json()["id"]


def _balance(token: str, acc: int) -> Decimal:
    r = client.get(f"/accounts/{acc}", headers=_h(token))
    return Decimal(r.json()["current_balance"])


@pytest.fixture
def setup_a():
    token = _register("a@ex.com")
    acc = _create_acc(token, "1000.00")
    return {"token": token, "acc": acc}


CSV_HAPPY = (
    "data,descricao,valor\n"
    "2026-05-01,PAGTO UBER 123,-25.00\n"
    "2026-05-02,IFOOD pedido,-49.90\n"
    "2026-05-03,NETFLIX,-39.90\n"
    "2026-05-04,Salario,2500.00\n"
)


def _csv_file(content: str, filename: str = "extrato.csv", content_type: str = "text/csv"):
    return {"file": (filename, io.BytesIO(content.encode("utf-8")), content_type)}


# ----------------- happy path -----------------


def test_upload_csv_feliz_cria_transacoes_e_atualiza_saldo(setup_a) -> None:
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files=_csv_file(CSV_HAPPY),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created_count"] == 4
    assert body["errors"] == []
    # 1000 - 25 - 49.90 - 39.90 + 2500 = 3385.20
    assert _balance(setup_a["token"], setup_a["acc"]) == Decimal("3385.20")

    # confirma que as transacoes foram criadas
    r = client.get("/transactions?page_size=100", headers=_h(setup_a["token"]))
    assert r.json()["total"] == 4


# ----------------- validacoes -----------------


def test_arquivo_sem_extensao_csv_400(setup_a) -> None:
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files={"file": ("extrato.txt", io.BytesIO(b"data,descricao,valor\n"), "text/plain")},
    )
    assert r.status_code == 400


def test_content_type_invalido_400(setup_a) -> None:
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files={"file": ("extrato.csv", io.BytesIO(b"data,descricao,valor\n"), "image/png")},
    )
    assert r.status_code == 400


def test_arquivo_vazio_400(setup_a) -> None:
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files=_csv_file(""),
    )
    assert r.status_code == 400


def test_arquivo_gigante_400(setup_a) -> None:
    # cria um arquivo > 2MB (cada linha ~30 bytes, gera 100k linhas ~= 3MB)
    big = "data,descricao,valor\n" + ("2026-05-01,UBER,-10.00\n" * 200_000)
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files=_csv_file(big),
    )
    assert r.status_code == 400


def test_account_de_outro_user_retorna_404(setup_a) -> None:
    token_b = _register("b@ex.com")
    r = client.post(
        "/imports/csv",
        headers=_h(token_b),
        data={"account_id": setup_a["acc"]},  # acc do A
        files=_csv_file(CSV_HAPPY),
    )
    assert r.status_code == 404


def test_sem_token_401(setup_a) -> None:
    r = client.post(
        "/imports/csv",
        data={"account_id": setup_a["acc"]},
        files=_csv_file(CSV_HAPPY),
    )
    assert r.status_code == 401


# ----------------- erros parciais e idempotencia logica -----------------


def test_csv_com_linhas_invalidas_processa_validas_e_reporta_erros(setup_a) -> None:
    csv = (
        "data,descricao,valor\n"
        "2026-05-01,UBER,-25.00\n"
        "bad,XXX,-10\n"
        "2026-05-03,NETFLIX,-39.90\n"
    )
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files=_csv_file(csv),
    )
    body = r.json()
    assert body["created_count"] == 2
    assert body["skipped_count"] == 1
    assert body["errors"][0]["line_number"] == 3
    # saldo: 1000 - 25 - 39.90 = 935.10
    assert _balance(setup_a["token"], setup_a["acc"]) == Decimal("935.10")


def test_csv_so_com_linhas_invalidas_nao_altera_saldo(setup_a) -> None:
    csv = (
        "data,descricao,valor\n"
        "bad,X,-10\n"
        ",,\n"
        "2026-05-01,,-5\n"  # descricao vazia
    )
    saldo_antes = _balance(setup_a["token"], setup_a["acc"])
    r = client.post(
        "/imports/csv",
        headers=_h(setup_a["token"]),
        data={"account_id": setup_a["acc"]},
        files=_csv_file(csv),
    )
    body = r.json()
    assert body["created_count"] == 0
    assert _balance(setup_a["token"], setup_a["acc"]) == saldo_antes
