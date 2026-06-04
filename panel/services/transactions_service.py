"""Service de transações (S26-T01).

`list_transactions` é cacheado por 60s (chave inclui token, filtros e base_url).
As mutações invalidam o cache de transações E o de contas (uma transação altera
o saldo das contas), garantindo leitura fresca após qualquer alteração.
`get_transaction` (detalhe) não é cacheado.
"""

from __future__ import annotations

import streamlit as st

import api
from services import accounts_service


@st.cache_data(ttl=60)
def list_transactions(
    token: str,
    *,
    page: int = 1,
    page_size: int = 100,
    date_from: str | None = None,
    date_to: str | None = None,
    type_: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    search: str | None = None,
    base_url: str = api.DEFAULT_BASE_URL,
) -> dict:
    return api.list_transactions(
        token,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        type_=type_,
        account_id=account_id,
        category_id=category_id,
        search=search,
        base_url=base_url,
    )


def get_transaction(token: str, transaction_id: int, base_url: str = api.DEFAULT_BASE_URL) -> dict:
    return api.get_transaction(token, transaction_id, base_url=base_url)


def _invalidate() -> None:
    list_transactions.clear()
    # saldos das contas mudam com a transação.
    accounts_service.clear_cache()


def create_transaction(token: str, base_url: str = api.DEFAULT_BASE_URL, **fields) -> dict:
    result = api.create_transaction(token, base_url=base_url, **fields)
    _invalidate()
    return result


def update_transaction(
    token: str, transaction_id: int, base_url: str = api.DEFAULT_BASE_URL, **fields
) -> dict:
    result = api.update_transaction(token, transaction_id, base_url=base_url, **fields)
    _invalidate()
    return result


def delete_transaction(
    token: str, transaction_id: int, base_url: str = api.DEFAULT_BASE_URL
) -> None:
    api.delete_transaction(token, transaction_id, base_url=base_url)
    _invalidate()


def clear_cache() -> None:
    list_transactions.clear()
