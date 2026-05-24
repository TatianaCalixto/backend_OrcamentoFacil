"""Testes unitarios do parser CSV e categorizacao automatica (S09-T02)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.imports.parser import (
    FALLBACK_CATEGORY_NAME,
    parse_csv,
)
from app.transactions.models import TransactionType


def _b(s: str) -> bytes:
    return s.encode("utf-8")


def test_csv_vazio_retorna_erro() -> None:
    r = parse_csv(b"")
    assert r.rows == []
    assert any("vazio" in e.message for e in r.errors)


def test_header_faltando_colunas_retorna_erro() -> None:
    r = parse_csv(_b("foo,bar\n1,2\n"))
    assert r.rows == []
    assert any("header invalido" in e.message for e in r.errors)


def test_parse_csv_minimo_virgula() -> None:
    csv = (
        "data,descricao,valor\n" "2026-05-01,Pagamento UBER,-20.00\n" "2026-05-02,Salario,2500.00\n"
    )
    r = parse_csv(_b(csv))
    assert r.errors == []
    assert len(r.rows) == 2
    a, b = r.rows
    assert a.date == date(2026, 5, 1)
    assert a.amount == Decimal("20.00")
    assert a.type == TransactionType.EXPENSE
    assert a.suggested_category_name == "Transporte"
    assert b.amount == Decimal("2500.00")
    assert b.type == TransactionType.INCOME


def test_parse_csv_pontoevirgula_e_valor_br() -> None:
    csv = (
        "data;descricao;valor\n"
        "01/05/2026;Compras IFOOD;-R$ 49,90\n"
        "02/05/2026;Devolucao;R$ 1.234,56\n"
    )
    r = parse_csv(_b(csv))
    assert r.errors == []
    assert r.rows[0].amount == Decimal("49.90")
    assert r.rows[0].suggested_category_name == "Alimentacao"
    assert r.rows[1].amount == Decimal("1234.56")
    assert r.rows[1].type == TransactionType.INCOME


def test_parse_csv_aceita_descricao_acentuada_no_header() -> None:
    # "descrição" (com acento) precisa virar "descricao" depois da normalizacao
    csv = "data,descrição,valor\n2026-05-01,NETFLIX,-39.90\n"
    r = parse_csv(csv.encode("utf-8"))
    assert r.errors == []
    assert r.rows[0].suggested_category_name == "Assinaturas"


def test_parse_csv_fallback_outros_quando_nao_bate_regra() -> None:
    csv = "data,descricao,valor\n2026-05-01,Conta de luz,-150\n"
    r = parse_csv(_b(csv))
    assert r.rows[0].suggested_category_name == FALLBACK_CATEGORY_NAME


def test_parse_csv_linha_invalida_vai_para_erros() -> None:
    csv = (
        "data,descricao,valor\n"
        "2026-05-01,UBER,-20.00\n"
        "bad-date,FOO,-10\n"
        "2026-05-03,,-5\n"  # descricao vazia
        "2026-05-04,SPOTIFY,zero\n"  # valor invalido
        "2026-05-05,FOO,0\n"  # valor zero
    )
    r = parse_csv(_b(csv))
    assert len(r.rows) == 1
    assert len(r.errors) == 4
    nums = {e.line_number for e in r.errors}
    assert nums == {3, 4, 5, 6}


def test_parse_csv_pula_linhas_em_branco() -> None:
    csv = "data,descricao,valor\n2026-05-01,UBER,-20\n\n2026-05-02,UBER,-10\n"
    r = parse_csv(_b(csv))
    assert len(r.rows) == 2
    assert r.errors == []


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("PAGTO UBER 123", "Transporte"),
        ("ifood pedido", "Alimentacao"),
        ("Assinatura NETFLIX", "Assinaturas"),
        ("Compra DROGARIA SP", "Saude"),
        ("Padaria do bairro", FALLBACK_CATEGORY_NAME),
    ],
)
def test_regras_de_categorizacao(description: str, expected: str) -> None:
    csv = f"data,descricao,valor\n2026-05-01,{description},-10\n"
    r = parse_csv(_b(csv))
    assert r.rows[0].suggested_category_name == expected
