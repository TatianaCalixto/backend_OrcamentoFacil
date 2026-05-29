"""Testes do CRUD de transacoes no wrapper api.py + helpers de UI (S18).

Mocka requests.* para nao depender de backend rodando.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# garante que panel/ esta no sys.path para importar api.py
PANEL_DIR = Path(__file__).resolve().parent.parent
if str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))

import api  # noqa: E402
from ui import filter_categories_by_type  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> object:
        return self._payload


# ----- create_transaction -----


def test_create_transaction_envia_amount_string_e_omite_opcionais_none() -> None:
    fake = _FakeResponse(201, {"id": 1})
    with patch("api.requests.post", return_value=fake) as mock_post:
        api.create_transaction(
            "tok",
            account_id=10,
            category_id=20,
            type="expense",
            amount=123.45,
            date="2026-05-24",
            base_url="http://b",
        )
    args, kwargs = mock_post.call_args
    assert args[0] == "http://b/transactions"
    payload = kwargs["json"]
    assert payload["account_id"] == 10
    assert payload["category_id"] == 20
    assert payload["type"] == "expense"
    assert payload["amount"] == "123.45"
    assert isinstance(payload["amount"], str)
    assert payload["date"] == "2026-05-24"
    assert payload["is_recurring"] is False
    assert "description" not in payload
    assert "payment_method" not in payload
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


def test_create_transaction_formata_amount_com_duas_casas() -> None:
    fake = _FakeResponse(201, {"id": 2})
    with patch("api.requests.post", return_value=fake) as mock_post:
        api.create_transaction(
            "tok",
            account_id=1,
            category_id=1,
            type="income",
            amount=10,
            date="2026-05-24",
            base_url="http://b",
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["amount"] == "10.00"


def test_create_transaction_inclui_opcionais_quando_informados() -> None:
    fake = _FakeResponse(201, {"id": 3})
    with patch("api.requests.post", return_value=fake) as mock_post:
        api.create_transaction(
            "tok",
            account_id=1,
            category_id=2,
            type="expense",
            amount=5.5,
            date="2026-05-24",
            description="Almoco",
            payment_method="pix",
            is_recurring=True,
            base_url="http://b",
        )
    payload = mock_post.call_args.kwargs["json"]
    assert payload["description"] == "Almoco"
    assert payload["payment_method"] == "pix"
    assert payload["is_recurring"] is True


def test_create_transaction_erro_422_levanta_api_error() -> None:
    fake = _FakeResponse(422, {"detail": "campo invalido"})
    with patch("api.requests.post", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.create_transaction(
                "tok",
                account_id=1,
                category_id=1,
                type="expense",
                amount=1.0,
                date="2026-05-24",
                base_url="http://b",
            )
    assert exc_info.value.status_code == 422
    assert "invalido" in exc_info.value.detail


# ----- filter_categories_by_type -----


def test_filter_categories_by_type_filtra_corretamente() -> None:
    cats = [
        {"id": 1, "name": "Salario", "type": "income"},
        {"id": 2, "name": "Aluguel", "type": "expense"},
        {"id": 3, "name": "Freelance", "type": "income"},
        {"id": 4, "name": "Mercado", "type": "expense"},
    ]
    inc = filter_categories_by_type(cats, "income")
    assert [c["id"] for c in inc] == [1, 3]
    exp = filter_categories_by_type(cats, "expense")
    assert [c["id"] for c in exp] == [2, 4]


def test_filter_categories_by_type_sem_filtro_retorna_tudo() -> None:
    cats = [{"id": 1, "type": "income"}, {"id": 2, "type": "expense"}]
    assert filter_categories_by_type(cats, None) == cats
    assert filter_categories_by_type(cats, "") == cats


def test_filter_categories_by_type_ignora_sem_campo_type() -> None:
    cats = [
        {"id": 1, "type": "income"},
        {"id": 2},  # sem type
        {"id": 3, "type": "expense"},
    ]
    assert [c["id"] for c in filter_categories_by_type(cats, "income")] == [1]


# ----- update_transaction -----


def test_update_transaction_omite_campos_none() -> None:
    fake = _FakeResponse(200, {"id": 5})
    with patch("api.requests.patch", return_value=fake) as mock_patch:
        api.update_transaction(
            "tok",
            5,
            description="novo texto",
            base_url="http://b",
        )
    args, kwargs = mock_patch.call_args
    assert args[0] == "http://b/transactions/5"
    payload = kwargs["json"]
    assert payload == {"description": "novo texto"}


def test_update_transaction_envia_amount_string_quando_informado() -> None:
    fake = _FakeResponse(200, {"id": 6})
    with patch("api.requests.patch", return_value=fake) as mock_patch:
        api.update_transaction(
            "tok",
            6,
            amount=99.9,
            type="income",
            is_recurring=False,
            base_url="http://b",
        )
    payload = mock_patch.call_args.kwargs["json"]
    assert payload["amount"] == "99.90"
    assert payload["type"] == "income"
    assert payload["is_recurring"] is False
    # nao informados ficam fora
    assert "description" not in payload
    assert "payment_method" not in payload
    assert "account_id" not in payload


def test_update_transaction_erro_levanta_api_error() -> None:
    fake = _FakeResponse(404, {"detail": "transacao nao encontrada"})
    with patch("api.requests.patch", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.update_transaction("tok", 999, description="x", base_url="http://b")
    assert exc_info.value.status_code == 404
    assert "encontrada" in exc_info.value.detail


# ----- delete_transaction -----


def test_delete_transaction_url_correta_e_retorna_none() -> None:
    fake = _FakeResponse(204, None)
    with patch("api.requests.delete", return_value=fake) as mock_delete:
        result = api.delete_transaction("tok", 77, base_url="http://b")
    args, kwargs = mock_delete.call_args
    assert args[0] == "http://b/transactions/77"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert result is None


def test_delete_transaction_erro_levanta_api_error() -> None:
    fake = _FakeResponse(403, {"detail": "sem permissao"})
    with patch("api.requests.delete", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.delete_transaction("tok", 1, base_url="http://b")
    assert exc_info.value.status_code == 403


# ----- get_transaction -----


def test_get_transaction_url_correta() -> None:
    fake = _FakeResponse(200, {"id": 3, "amount": "10.00"})
    with patch("api.requests.get", return_value=fake) as mock_get:
        result = api.get_transaction("tok", 3, base_url="http://b")
    args, kwargs = mock_get.call_args
    assert args[0] == "http://b/transactions/3"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert result["id"] == 3
