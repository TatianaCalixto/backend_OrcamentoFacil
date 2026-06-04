"""Importacao de transacoes via CSV (S18-T04)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import api
from services import accounts_service, transactions_service
from ui import render_header

st.set_page_config(page_title="Importar CSV - OrcaFacil", layout="wide")

if "token" not in st.session_state:
    st.warning("Faca login na pagina principal para acessar.")
    st.stop()

render_header()

token = st.session_state["token"]
api_base = st.session_state.get("api_base", api.DEFAULT_BASE_URL)

st.title("Importar CSV")
st.write(
    "Selecione a conta-alvo e o arquivo CSV. As linhas validas serao importadas;"
    " linhas com erro vem listadas no fim com o motivo."
)

try:
    accounts = accounts_service.list_accounts(token, base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar contas: {e.detail}")
    st.stop()

if not accounts:
    st.warning("Cadastre ao menos uma conta antes de importar.")
    st.stop()

acc_id = st.selectbox(
    "Conta-alvo",
    options=[a["id"] for a in accounts],
    format_func=lambda i: next(a["name"] for a in accounts if a["id"] == i),
)

upload = st.file_uploader("Arquivo CSV", type=["csv"])

disabled = upload is None or acc_id is None

if st.button("Importar", type="primary", disabled=disabled):
    try:
        result = api.import_csv(
            token,
            account_id=int(acc_id),
            file_name=upload.name,
            file_bytes=upload.getvalue(),
            base_url=api_base,
        )
        transactions_service.clear_cache()
        accounts_service.clear_cache()
    except api.ApiError as e:
        st.error(e.detail)
    else:
        c1, c2 = st.columns(2)
        c1.metric("Importadas", result.get("imported", 0))
        c2.metric("Erros", result.get("failed", 0))
        errors = result.get("errors") or []
        if errors:
            st.subheader("Erros")
            st.dataframe(
                pd.DataFrame(errors),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Importacao concluida sem erros.")
