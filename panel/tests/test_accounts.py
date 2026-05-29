"""Testes do CRUD de contas no wrapper api.py (S17-T04).

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


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> object:
        return self._payload


# ----- create_account -----


def test_create_account_envia_payload_correto() -> None:
    fake = _FakeResponse(
        201,
        {
            "id": 7,
            "user_id": 1,
            "name": "Nubank",
            "type": "checking",
            "initial_balance": "100.50",
            "current_balance": "100.50",
            "is_active": True,
            "created_at": "2026-05-24T00:00:00Z",
        },
    )
    with patch("api.requests.post", return_value=fake) as mock_post:
        result = api.create_account(
            "tok",
            name="Nubank",
            type="checking",
            initial_balance=100.5,
            base_url="http://b",
        )
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://b/accounts"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert kwargs["json"] == {
        "name": "Nubank",
        "type": "checking",
        "initial_balance": 100.5,
    }
    assert result["id"] == 7
    assert result["name"] == "Nubank"


def test_create_account_erro_levanta_api_error() -> None:
    fake = _FakeResponse(400, {"detail": "nome duplicado"})
    with patch("api.requests.post", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.create_account(
                "tok",
                name="X",
                type="cash",
                initial_balance=0.0,
                base_url="http://b",
            )
    assert exc_info.value.status_code == 400
    assert "duplicado" in exc_info.value.detail


# ----- update_account -----


def test_update_account_envia_apenas_campos_nao_none() -> None:
    fake = _FakeResponse(
        200,
        {
            "id": 5,
            "user_id": 1,
            "name": "Novo Nome",
            "type": "checking",
            "initial_balance": "0",
            "current_balance": "0",
            "is_active": True,
            "created_at": "2026-05-24T00:00:00Z",
        },
    )
    with patch("api.requests.patch", return_value=fake) as mock_patch:
        api.update_account("tok", 5, name="Novo Nome", base_url="http://b")
    args, kwargs = mock_patch.call_args
    assert args[0] == "http://b/accounts/5"
    assert kwargs["json"] == {"name": "Novo Nome"}
    assert "type" not in kwargs["json"]
    assert "is_active" not in kwargs["json"]


def test_update_account_envia_payload_completo() -> None:
    fake = _FakeResponse(
        200,
        {
            "id": 9,
            "user_id": 1,
            "name": "C",
            "type": "savings",
            "initial_balance": "0",
            "current_balance": "0",
            "is_active": False,
            "created_at": "2026-05-24T00:00:00Z",
        },
    )
    with patch("api.requests.patch", return_value=fake) as mock_patch:
        api.update_account(
            "tok",
            9,
            name="C",
            type="savings",
            is_active=False,
            base_url="http://b",
        )
    kwargs = mock_patch.call_args.kwargs
    assert kwargs["json"] == {"name": "C", "type": "savings", "is_active": False}
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


# ----- delete_account -----


def test_delete_account_envia_id_correto() -> None:
    fake = _FakeResponse(204, None)
    with patch("api.requests.delete", return_value=fake) as mock_delete:
        result = api.delete_account("tok", 42, base_url="http://b")
    args, kwargs = mock_delete.call_args
    assert args[0] == "http://b/accounts/42"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert result is None


def test_delete_account_erro_levanta_api_error() -> None:
    fake = _FakeResponse(404, {"detail": "conta nao encontrada"})
    with patch("api.requests.delete", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.delete_account("tok", 999, base_url="http://b")
    assert exc_info.value.status_code == 404
    assert "encontrada" in exc_info.value.detail
