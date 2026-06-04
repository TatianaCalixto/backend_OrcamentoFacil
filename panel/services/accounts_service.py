"""Service de contas (S26-T01).

`list_accounts` é cacheado por 60s (chave inclui token e base_url). As mutações
(create/update/delete) invalidam o cache para a próxima leitura buscar fresco.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

import api


@st.cache_data(ttl=60)
def list_accounts(token: str, base_url: str = api.DEFAULT_BASE_URL) -> list[dict]:
    return api.list_accounts(token, base_url=base_url)


def create_account(
    token: str,
    *,
    name: str,
    type: str,
    initial_balance: float,
    base_url: str = api.DEFAULT_BASE_URL,
) -> dict:
    result = api.create_account(
        token, name=name, type=type, initial_balance=initial_balance, base_url=base_url
    )
    list_accounts.clear()
    return result


def update_account(
    token: str,
    account_id: int,
    *,
    name: str | None = None,
    type: str | None = None,
    is_active: bool | None = None,
    base_url: str = api.DEFAULT_BASE_URL,
) -> dict:
    result = api.update_account(
        token, account_id, name=name, type=type, is_active=is_active, base_url=base_url
    )
    list_accounts.clear()
    return result


def delete_account(token: str, account_id: int, base_url: str = api.DEFAULT_BASE_URL) -> None:
    api.delete_account(token, account_id, base_url=base_url)
    list_accounts.clear()


def clear_cache() -> None:
    """Invalida o cache de contas (ex.: quando uma transação altera saldos)."""
    list_accounts.clear()


# Reexporta para conveniência das páginas.
ApiError: Any = api.ApiError
