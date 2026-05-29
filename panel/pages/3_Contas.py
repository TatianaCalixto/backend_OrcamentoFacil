"""CRUD de contas (S17-T04)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import api
from ui import render_header

st.set_page_config(page_title="Contas - OrcaFacil", layout="wide")

if "token" not in st.session_state:
    st.warning("Faca login na pagina principal para acessar.")
    st.stop()

render_header()

token = st.session_state["token"]
api_base = st.session_state.get("api_base", api.DEFAULT_BASE_URL)

st.title("Contas")

TYPE_OPTIONS = ["checking", "savings", "credit_card", "cash"]
TYPE_LABELS = {
    "checking": "Corrente",
    "savings": "Poupanca",
    "credit_card": "Cartao",
    "cash": "Dinheiro",
}

# ----- carregar lista -----
try:
    accounts = api.list_accounts(token, base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar contas: {e.detail}")
    st.stop()

if accounts:
    df = pd.DataFrame(accounts)
    df["initial_balance"] = df["initial_balance"].astype(float)
    df["current_balance"] = df["current_balance"].astype(float)
    df["Tipo"] = df["type"].map(TYPE_LABELS).fillna(df["type"])
    df["Ativa"] = df["is_active"].map(lambda v: "OK" if v else "X")
    view = df[["name", "Tipo", "initial_balance", "current_balance", "Ativa"]].rename(
        columns={
            "name": "Nome",
            "initial_balance": "Saldo Inicial",
            "current_balance": "Saldo Atual",
        }
    )
    st.dataframe(view, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma conta cadastrada ainda.")

# ----- criar -----
with st.expander("+ Nova conta"):
    with st.form("form_nova_conta", clear_on_submit=True):
        new_name = st.text_input("Nome", max_chars=100)
        new_type = st.selectbox(
            "Tipo",
            options=TYPE_OPTIONS,
            format_func=lambda v: TYPE_LABELS[v],
        )
        new_balance = st.number_input(
            "Saldo inicial",
            min_value=0.0,
            step=0.01,
            format="%.2f",
        )
        submit_new = st.form_submit_button("Criar")
        if submit_new:
            if not new_name.strip():
                st.error("Nome e obrigatorio.")
            else:
                try:
                    api.create_account(
                        token,
                        name=new_name.strip(),
                        type=new_type,
                        initial_balance=float(new_balance),
                        base_url=api_base,
                    )
                    st.success("Conta criada")
                    st.rerun()
                except api.ApiError as e:
                    st.error(e.detail)

# ----- editar -----
if accounts:
    with st.expander("Editar conta"):
        acc_by_id = {a["id"]: a for a in accounts}
        edit_id = st.selectbox(
            "Conta para editar",
            options=list(acc_by_id.keys()),
            format_func=lambda i: acc_by_id[i]["name"],
            key="edit_select",
        )
        current = acc_by_id[edit_id]
        with st.form("form_editar_conta"):
            ed_name = st.text_input("Nome", value=current["name"], max_chars=100)
            ed_type = st.selectbox(
                "Tipo",
                options=TYPE_OPTIONS,
                index=TYPE_OPTIONS.index(current["type"])
                if current["type"] in TYPE_OPTIONS
                else 0,
                format_func=lambda v: TYPE_LABELS[v],
            )
            ed_active = st.toggle("Ativa", value=bool(current["is_active"]))
            submit_edit = st.form_submit_button("Salvar")
            if submit_edit:
                if not ed_name.strip():
                    st.error("Nome e obrigatorio.")
                else:
                    try:
                        api.update_account(
                            token,
                            edit_id,
                            name=ed_name.strip(),
                            type=ed_type,
                            is_active=ed_active,
                            base_url=api_base,
                        )
                        st.success("Conta atualizada")
                        st.rerun()
                    except api.ApiError as e:
                        st.error(e.detail)

    with st.expander("Excluir conta"):
        del_id = st.selectbox(
            "Conta para excluir",
            options=list(acc_by_id.keys()),
            format_func=lambda i: acc_by_id[i]["name"],
            key="delete_select",
        )
        confirmado = st.checkbox("Confirmo a exclusao")
        if st.button("Excluir", type="primary", disabled=not confirmado):
            try:
                api.delete_account(token, del_id, base_url=api_base)
                st.success("Conta excluida")
                st.rerun()
            except api.ApiError as e:
                st.error(e.detail)
