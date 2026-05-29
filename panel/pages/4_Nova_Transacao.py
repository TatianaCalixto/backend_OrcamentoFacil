"""Nova transacao (S18-T01)."""

from __future__ import annotations

from datetime import date as date_cls

import streamlit as st

import api
from ui import filter_categories_by_type, render_header

st.set_page_config(page_title="Nova Transacao - OrcaFacil", layout="wide")

if "token" not in st.session_state:
    st.warning("Faca login na pagina principal para acessar.")
    st.stop()

render_header()

token = st.session_state["token"]
api_base = st.session_state.get("api_base", api.DEFAULT_BASE_URL)

st.title("Nova transacao")

PAYMENT_OPTIONS = ["", "cash", "debit", "credit", "pix", "transfer", "other"]
PAYMENT_LABELS = {
    "": "(nao informado)",
    "cash": "Dinheiro",
    "debit": "Debito",
    "credit": "Credito",
    "pix": "Pix",
    "transfer": "Transferencia",
    "other": "Outro",
}

try:
    accounts = api.list_accounts(token, base_url=api_base)
    categories = api.list_categories(token, base_url=api_base)
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

with st.form("form_nova_transacao", clear_on_submit=True):
    amount = st.number_input(
        "Valor", min_value=0.0, step=0.01, format="%.2f", key="new_tx_amount"
    )
    when = st.date_input("Data", value=date_cls.today(), key="new_tx_date")
    acc_id = st.selectbox(
        "Conta",
        options=[a["id"] for a in accounts],
        format_func=lambda i: next(a["name"] for a in accounts if a["id"] == i),
        key="new_tx_account",
    )
    cat_id = st.selectbox(
        "Categoria",
        options=[c["id"] for c in cats_filtradas],
        format_func=lambda i: next(
            c["name"] for c in cats_filtradas if c["id"] == i
        ),
        key="new_tx_category",
    )
    description = st.text_input("Descricao (opcional)", key="new_tx_description")
    payment = st.selectbox(
        "Forma de pagamento",
        options=PAYMENT_OPTIONS,
        format_func=lambda v: PAYMENT_LABELS[v],
        key="new_tx_payment",
    )
    is_recurring = st.checkbox("Recorrente", key="new_tx_recurring")
    submit = st.form_submit_button("Criar")

if submit:
    if amount <= 0:
        st.error("Informe um valor maior que zero.")
    else:
        try:
            api.create_transaction(
                token,
                account_id=int(acc_id),
                category_id=int(cat_id),
                type=type_sel,
                amount=float(amount),
                date=when.isoformat(),
                description=description.strip() or None,
                payment_method=payment or None,
                is_recurring=bool(is_recurring),
                base_url=api_base,
            )
            st.success("Transacao criada")
            # Limpa campos controlados por chave antes do rerun.
            for k in (
                "new_tx_amount",
                "new_tx_description",
                "new_tx_payment",
                "new_tx_recurring",
            ):
                st.session_state.pop(k, None)
            st.rerun()
        except api.ApiError as e:
            st.error(e.detail)
