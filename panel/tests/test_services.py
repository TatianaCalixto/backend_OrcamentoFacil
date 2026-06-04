"""Testes da camada de services do painel (S26-T01).

Mocka `api.*` e valida: (1) as listas cacheiam (2a chamada = hit, sem refazer
a chamada à API); (2) mutações invalidam o cache; (3) mutação de transação
também invalida o cache de contas (saldos mudam); (4) filtros distintos geram
chaves de cache distintas.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PANEL_DIR = Path(__file__).resolve().parent.parent
if str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))

from services import accounts_service, categories_service, transactions_service  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_caches():
    accounts_service.list_accounts.clear()
    categories_service.list_categories.clear()
    transactions_service.list_transactions.clear()
    yield
    accounts_service.list_accounts.clear()
    categories_service.list_categories.clear()
    transactions_service.list_transactions.clear()


# ----- accounts -----


def test_list_accounts_cacheia_dentro_do_ttl() -> None:
    with patch("api.list_accounts", return_value=[{"id": 1}]) as m:
        a = accounts_service.list_accounts("tok")
        b = accounts_service.list_accounts("tok")
    assert a == b == [{"id": 1}]
    assert m.call_count == 1  # 2a chamada = cache hit


def test_create_account_invalida_cache() -> None:
    with patch("api.list_accounts", return_value=[{"id": 1}]) as m_list:
        accounts_service.list_accounts("tok")
        accounts_service.list_accounts("tok")
        assert m_list.call_count == 1
        with patch("api.create_account", return_value={"id": 2}) as m_create:
            accounts_service.create_account(
                "tok", name="Nubank", type="checking", initial_balance=0.0
            )
        m_create.assert_called_once()
        accounts_service.list_accounts("tok")  # cache invalidado -> refaz
    assert m_list.call_count == 2


def test_update_e_delete_account_invalidam_cache() -> None:
    with patch("api.list_accounts", return_value=[{"id": 1}]) as m_list:
        accounts_service.list_accounts("tok")
        with patch("api.update_account", return_value={"id": 1}):
            accounts_service.update_account("tok", 1, name="Novo")
        accounts_service.list_accounts("tok")
        assert m_list.call_count == 2
        with patch("api.delete_account", return_value=None):
            accounts_service.delete_account("tok", 1)
        accounts_service.list_accounts("tok")
    assert m_list.call_count == 3


# ----- categories -----


def test_list_categories_cacheia() -> None:
    with patch("api.list_categories", return_value=[{"id": 1, "type": "expense"}]) as m:
        categories_service.list_categories("tok")
        categories_service.list_categories("tok")
    assert m.call_count == 1


# ----- transactions -----


def test_list_transactions_cacheia_e_filtros_distintos_sao_chaves_distintas() -> None:
    with patch("api.list_transactions", return_value={"items": []}) as m:
        transactions_service.list_transactions("tok")
        transactions_service.list_transactions("tok")  # hit
        assert m.call_count == 1
        transactions_service.list_transactions("tok", type_="income")  # filtro novo = miss
        assert m.call_count == 2


def test_create_transaction_invalida_transacoes_e_contas() -> None:
    with (
        patch("api.list_transactions", return_value={"items": []}) as m_tx,
        patch("api.list_accounts", return_value=[{"id": 1}]) as m_acc,
    ):
        transactions_service.list_transactions("tok")
        accounts_service.list_accounts("tok")
        assert m_tx.call_count == 1
        assert m_acc.call_count == 1

        with patch("api.create_transaction", return_value={"id": 9}):
            transactions_service.create_transaction(
                "tok",
                account_id=1,
                category_id=1,
                type="expense",
                amount=10.0,
                date="2026-05-01",
            )

        transactions_service.list_transactions("tok")  # invalidado -> refaz
        accounts_service.list_accounts("tok")  # invalidacao cruzada (saldo mudou)
    assert m_tx.call_count == 2
    assert m_acc.call_count == 2


def test_delete_transaction_invalida_cache() -> None:
    with patch("api.list_transactions", return_value={"items": []}) as m_tx:
        transactions_service.list_transactions("tok")
        with patch("api.delete_transaction", return_value=None):
            transactions_service.delete_transaction("tok", 5)
        transactions_service.list_transactions("tok")
    assert m_tx.call_count == 2


def test_update_transaction_invalida_transacoes_e_contas() -> None:
    with (
        patch("api.list_transactions", return_value={"items": []}) as m_tx,
        patch("api.list_accounts", return_value=[{"id": 1}]) as m_acc,
    ):
        transactions_service.list_transactions("tok")
        accounts_service.list_accounts("tok")
        with patch("api.update_transaction", return_value={"id": 5}) as m_up:
            transactions_service.update_transaction("tok", 5, amount=10.0)
        m_up.assert_called_once()
        transactions_service.list_transactions("tok")
        accounts_service.list_accounts("tok")
    assert m_tx.call_count == 2
    assert m_acc.call_count == 2  # invalidacao cruzada


def test_get_transaction_nao_cacheado_delega_para_api() -> None:
    with patch("api.get_transaction", return_value={"id": 3}) as m:
        a = transactions_service.get_transaction("tok", 3)
        b = transactions_service.get_transaction("tok", 3)
    assert a == b == {"id": 3}
    assert m.call_count == 2  # detalhe nao e cacheado
