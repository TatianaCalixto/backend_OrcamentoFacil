"""Nova transacao (S18-T01)."""

from __future__ import annotations

import streamlit as st

import api
from components.transaction_form import transaction_form
from services import accounts_service, categories_service, transactions_service
from ui import filter_categories_by_type, render_header

st.set_page_config(page_title="Nova Transacao - OrcaFacil", layout="wide")

if "token" not in st.session_state:
    st.warning("Faca login na pagina principal para acessar.")
    st.stop()

render_header()

token = st.session_state["token"]
api_base = st.session_state.get("api_base", api.DEFAULT_BASE_URL)

st.title("Nova transacao")

try:
    accounts = accounts_service.list_accounts(token, base_url=api_base)
    categories = categories_service.list_categories(token, base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar dados auxiliares: {e.detail}")
    st.stop()

if not accounts:
    st.warning("Cadastre ao menos uma conta antes de criar transacoes.")
    st.stop()

# Tipo fica FORA do form para que a lista de categorias reaja sem submit.
type_sel = st.radio(
    "Tipo",
    options=["income", "expense"],
    horizontal=True,
    format_func=lambda v: "Receita" if v == "income" else "Despesa",
    key="new_tx_type",
)

cats_filtradas = filter_categories_by_type(categories, type_sel)

if not cats_filtradas:
    st.warning(
        f"Nenhuma categoria do tipo '{type_sel}' cadastrada. "
        "Crie uma categoria adequada antes de continuar."
    )
    st.stop()

submitted, values = transaction_form(
    accounts=accounts,
    categories=cats_filtradas,
    type_value=type_sel,
    submit_label="Criar",
    form_key="form_nova_transacao",
    clear_on_submit=True,
)

if submitted and values is not None:
    try:
        transactions_service.create_transaction(token, base_url=api_base, **values)
        st.success("Transacao criada")
        st.rerun()
    except api.ApiError as e:
        st.error(e.detail)
