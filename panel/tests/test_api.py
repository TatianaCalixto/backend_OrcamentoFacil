"""Smoke tests do wrapper de API (S15-T01).

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


def test_login_chama_endpoint_correto_e_retorna_tokens() -> None:
    fake = _FakeResponse(200, {"access_token": "a", "refresh_token": "r", "token_type": "bearer"})
    with patch("api.requests.post", return_value=fake) as mock_post:
        result = api.login("u@x", "p", base_url="http://b")
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://b/auth/login"
    assert kwargs["json"] == {"email": "u@x", "password": "p"}
    assert result["access_token"] == "a"


def test_login_falha_levanta_api_error() -> None:
    fake = _FakeResponse(401, {"detail": "credenciais invalidas"})
    with patch("api.requests.post", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.login("u@x", "wrong", base_url="http://b")
    assert exc_info.value.status_code == 401
    assert "credenciais" in exc_info.value.detail


def test_me_injeta_authorization_header() -> None:
    fake = _FakeResponse(200, {"id": 1, "name": "U", "email": "u@x", "created_at": "2026-05-24T00:00:00Z"})
    with patch("api.requests.get", return_value=fake) as mock_get:
        api.me("tok", base_url="http://b")
    args, kwargs = mock_get.call_args
    assert args[0] == "http://b/users/me"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


def test_list_transactions_passa_filtros_como_query_params() -> None:
    fake = _FakeResponse(200, {"items": [], "total": 0, "page": 1, "page_size": 50})
    with patch("api.requests.get", return_value=fake) as mock_get:
        api.list_transactions(
            "tok", page=2, page_size=50,
            date_from="2026-01-01", date_to="2026-12-31",
            type_="expense", account_id=3, category_id=4, search="UBER",
            base_url="http://b",
        )
    args, kwargs = mock_get.call_args
    assert args[0] == "http://b/transactions"
    p = kwargs["params"]
    assert p["page"] == 2
    assert p["page_size"] == 50
    assert p["date_from"] == "2026-01-01"
    assert p["date_to"] == "2026-12-31"
    assert p["type"] == "expense"
    assert p["account_id"] == 3
    assert p["category_id"] == 4
    assert p["search"] == "UBER"


def test_list_transactions_sem_filtros_so_envia_paginas() -> None:
    fake = _FakeResponse(200, {"items": [], "total": 0, "page": 1, "page_size": 100})
    with patch("api.requests.get", return_value=fake) as mock_get:
        api.list_transactions("tok", base_url="http://b")
    p = mock_get.call_args.kwargs["params"]
    assert set(p.keys()) == {"page", "page_size"}


def test_api_error_contem_status_e_detail() -> None:
    e = api.ApiError(500, "boom")
    assert e.status_code == 500
    assert e.detail == "boom"
    assert "500" in str(e)
