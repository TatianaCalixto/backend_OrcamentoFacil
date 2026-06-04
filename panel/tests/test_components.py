"""Testes dos componentes do painel (S26-T03/T05) via streamlit AppTest.

Cobre o `transaction_form` nos dois modos (criação e edição) e o `filters_bar`.
Usa AppTest.from_function para rodar o componente num runtime simulado, definir
valores nos widgets, acionar o submit e inspecionar o resultado guardado em
st.session_state.

Obs.: AppTest.from_function executa o código da função num módulo ISOLADO, então
cada harness precisa ser autossuficiente (define dados e imports internamente).
"""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

PANEL_DIR = Path(__file__).resolve().parent.parent
if str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))


# --------------------------- transaction_form: criação ---------------------------


def _create_harness() -> None:
    import streamlit as st

    from components.transaction_form import transaction_form

    accounts = [{"id": 1, "name": "Nubank"}, {"id": 2, "name": "Itau"}]
    categories = [
        {"id": 10, "name": "Salario", "type": "income"},
        {"id": 11, "name": "Bonus", "type": "income"},
    ]
    submitted, values = transaction_form(
        accounts=accounts,
        categories=categories,
        type_value="income",
        submit_label="Criar",
        form_key="f_create",
    )
    st.session_state["_result"] = (submitted, values)


def test_transaction_form_modo_criacao_defaults_e_submit() -> None:
    at = AppTest.from_function(_create_harness)
    at.run()
    assert at.session_state["_result"][0] is False
    assert at.number_input[0].value == 0.0  # default do modo criação
    at.number_input[0].set_value(50.0)
    at.text_input[0].set_value("Salario maio")
    at.button[0].click().run()
    submitted, values = at.session_state["_result"]
    assert submitted is True
    assert values is not None
    assert values["type"] == "income"
    assert values["amount"] == 50.0
    assert values["account_id"] == 1
    assert values["category_id"] == 10
    assert values["description"] == "Salario maio"


def test_transaction_form_valor_zero_invalido_retorna_none() -> None:
    at = AppTest.from_function(_create_harness)
    at.run()
    at.button[0].click().run()  # valor permanece 0.0 -> validação falha
    submitted, values = at.session_state["_result"]
    assert submitted is True
    assert values is None
    assert len(at.error) >= 1


# --------------------------- transaction_form: edição ---------------------------


def _edit_harness() -> None:
    from datetime import date

    import streamlit as st

    from components.transaction_form import transaction_form

    accounts = [{"id": 1, "name": "Nubank"}, {"id": 2, "name": "Itau"}]
    categories = [
        {"id": 10, "name": "Salario", "type": "income"},
        {"id": 11, "name": "Bonus", "type": "income"},
    ]
    submitted, values = transaction_form(
        accounts=accounts,
        categories=categories,
        type_value="income",
        initial={
            "amount": 99.9,
            "date": date(2026, 5, 1),
            "account_id": 2,
            "category_id": 11,
            "description": "Bonus anual",
            "payment_method": "pix",
            "is_recurring": True,
        },
        submit_label="Salvar",
        form_key="f_edit",
    )
    st.session_state["_result"] = (submitted, values)


def test_transaction_form_modo_edicao_pre_preenche_e_submete() -> None:
    at = AppTest.from_function(_edit_harness)
    at.run()
    assert at.number_input[0].value == 99.9
    assert at.selectbox[0].value == 2  # conta Itau pré-selecionada
    assert at.selectbox[1].value == 11  # categoria Bonus pré-selecionada
    assert at.text_input[0].value == "Bonus anual"
    assert at.checkbox[0].value is True
    at.button[0].click().run()
    submitted, values = at.session_state["_result"]
    assert submitted is True
    assert values["account_id"] == 2
    assert values["category_id"] == 11
    assert values["amount"] == 99.9
    assert values["payment_method"] == "pix"
    assert values["is_recurring"] is True
    assert values["date"] == "2026-05-01"


# --------------------------- filters_bar (S26-T05) + persistência (S26-T04) -----


def test_merge_filters_fallback_por_chave() -> None:
    from components.filters_bar import merge_filters

    defaults = {"type": "", "search": "", "account_id": 0}
    # sem persistido -> tudo default
    assert merge_filters(None, defaults) == defaults
    assert merge_filters({}, defaults) == defaults
    # persistido sobrescreve só as chaves presentes (fallback nas demais)
    assert merge_filters({"type": "income"}, defaults) == {
        "type": "income",
        "search": "",
        "account_id": 0,
    }


def _filters_harness() -> None:
    import streamlit as st

    from components.filters_bar import filters_bar

    specs = [
        {
            "key": "type",
            "label": "Tipo",
            "kind": "select",
            "default": "",
            "options": ["", "income", "expense"],
            "format_func": lambda v: v or "(todos)",
        },
        {"key": "search", "label": "Busca", "kind": "text", "default": ""},
    ]
    st.session_state["_vals"] = filters_bar(specs, state_key="transactions_filters", n_cols=2)


def test_filters_bar_renderiza_specs_configuraveis_e_defaults() -> None:
    at = AppTest.from_function(_filters_harness)
    at.run()
    # renderizou exatamente os filtros configurados
    assert len(at.selectbox) == 1
    assert len(at.text_input) == 1
    # defaults aplicados e persistidos sob a chave configurada
    assert at.session_state["_vals"] == {"type": "", "search": ""}
    assert at.session_state["transactions_filters"] == {"type": "", "search": ""}


def test_filters_bar_persiste_selecao_entre_reruns() -> None:
    at = AppTest.from_function(_filters_harness)
    at.run()
    at.selectbox[0].set_value("expense")
    at.text_input[0].set_value("aluguel")
    at.run()  # rerun: valores devem persistir
    persistido = at.session_state["transactions_filters"]
    assert persistido["type"] == "expense"
    assert persistido["search"] == "aluguel"
    # e continuam após mais um rerun sem alterar nada (estabilidade)
    at.run()
    assert at.session_state["transactions_filters"]["type"] == "expense"


def _filters_guard_harness() -> None:
    import streamlit as st

    from components.filters_bar import filters_bar

    # simula valor persistido invalido (conta 999 que nao existe mais nas opcoes)
    st.session_state["transactions_filters"] = {"account_id": 999}
    specs = [
        {
            "key": "account_id",
            "label": "Conta",
            "kind": "select",
            "default": 0,
            "options": [0, 1, 2],
            "format_func": lambda i: str(i),
        }
    ]
    st.session_state["_vals"] = filters_bar(specs, state_key="transactions_filters", n_cols=1)


def test_filters_bar_reseta_select_quando_valor_persistido_fora_das_opcoes() -> None:
    at = AppTest.from_function(_filters_guard_harness)
    at.run()
    # 999 nao esta em [0,1,2] -> volta ao default valido (0)
    assert at.session_state["_vals"]["account_id"] == 0
    assert at.selectbox[0].value == 0


def _filters_invalid_kind_harness() -> None:
    import streamlit as st

    from components.filters_bar import filters_bar

    try:
        filters_bar(
            [{"key": "x", "label": "X", "kind": "slider", "default": 0}],
            state_key="k",
        )
    except ValueError as e:
        st.session_state["_err"] = str(e)


def test_filters_bar_kind_desconhecido_levanta() -> None:
    at = AppTest.from_function(_filters_invalid_kind_harness)
    at.run()
    assert "slider" in at.session_state["_err"]
