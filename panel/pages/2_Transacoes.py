"""Transacoes com filtros e exportacao CSV/XLSX (S15-T03)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

import api
from components.filters_bar import filters_bar
from components.transaction_form import transaction_form
from services import accounts_service, categories_service, transactions_service
from ui import filter_categories_by_type, render_header

st.set_page_config(page_title="Transacoes — OrcaFacil", layout="wide")

if "token" not in st.session_state:
    st.warning("Faca login na pagina principal para acessar.")
    st.stop()

render_header()

token = st.session_state["token"]
api_base = st.session_state.get("api_base", api.DEFAULT_BASE_URL)

st.title("Transacoes")

# ----- carregar listas auxiliares -----
try:
    accounts = accounts_service.list_accounts(token, base_url=api_base)
    categories = categories_service.list_categories(token, base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar dados auxiliares: {e.detail}")
    st.stop()

acc_label = {0: "(todas)"} | {a["id"]: a["name"] for a in accounts}
cat_label = {0: "(todas)"} | {c["id"]: c["name"] for c in categories}

# ----- filtros (persistidos em session_state, via filters_bar) -----
today = date.today()
default_from = today.replace(day=1)

filtros = filters_bar(
    [
        {"key": "date_from", "label": "De", "kind": "date", "default": default_from},
        {"key": "date_to", "label": "Ate", "kind": "date", "default": today},
        {
            "key": "type",
            "label": "Tipo",
            "kind": "select",
            "default": "",
            "options": ["", "income", "expense"],
            "format_func": lambda v: v or "(todos)",
        },
        {"key": "search", "label": "Busca (descricao)", "kind": "text", "default": ""},
        {
            "key": "account_id",
            "label": "Conta",
            "kind": "select",
            "default": 0,
            "options": list(acc_label.keys()),
            "format_func": lambda i: acc_label[i],
        },
        {
            "key": "category_id",
            "label": "Categoria",
            "kind": "select",
            "default": 0,
            "options": list(cat_label.keys()),
            "format_func": lambda i: cat_label[i],
        },
    ],
    state_key="transactions_filters",
    n_cols=4,
)
date_from = filtros["date_from"]
date_to = filtros["date_to"]
type_sel = filtros["type"]
search = filtros["search"]
acc_id = filtros["account_id"]
cat_id = filtros["category_id"]

# ----- buscar transacoes (paginas para nao perder dados) -----
@st.cache_data(show_spinner=False, ttl=60)
def _fetch_all(
    token: str, api_base: str,
    date_from: str, date_to: str, type_: str | None,
    account_id: int | None, category_id: int | None, search: str | None,
) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        resp = transactions_service.list_transactions(
            token,
            page=page, page_size=200,
            date_from=date_from, date_to=date_to,
            type_=type_ or None,
            account_id=account_id,
            category_id=category_id,
            search=search or None,
            base_url=api_base,
        )
        items.extend(resp["items"])
        total = resp["total"]
        page_size = resp["page_size"]
        if page * page_size >= total or not resp["items"]:
            break
        page += 1
    return items


with st.spinner("Carregando transacoes..."):
    try:
        items = _fetch_all(
            token, api_base,
            date_from.isoformat(), date_to.isoformat(),
            type_sel or None,
            acc_id if acc_id else None,
            cat_id if cat_id else None,
            search or None,
        )
    except api.ApiError as e:
        st.error(f"Erro: {e.detail}")
        st.stop()

if not items:
    st.info("Nenhuma transacao no filtro atual.")
    st.stop()

df = pd.DataFrame(items)
df["amount"] = df["amount"].astype(float)
acc_by_id = {a["id"]: a["name"] for a in accounts}
cat_by_id = {c["id"]: c["name"] for c in categories}
df["account"] = df["account_id"].map(acc_by_id)
df["category"] = df["category_id"].map(cat_by_id)
view = df[["date", "type", "amount", "description", "account", "category"]].rename(
    columns={
        "date": "Data", "type": "Tipo", "amount": "Valor",
        "description": "Descricao", "account": "Conta", "category": "Categoria",
    }
)

st.dataframe(view, use_container_width=True, hide_index=True)

# ----- exportacao -----
st.subheader("Exportar")
col_csv, col_xlsx = st.columns(2)

with col_csv:
    csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Baixar CSV",
        data=csv_bytes,
        file_name=f"transacoes_{date_from}_{date_to}.csv",
        mime="text/csv",
    )

with col_xlsx:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        view.to_excel(writer, index=False, sheet_name="Transacoes")
    st.download_button(
        label="Baixar XLSX",
        data=buf.getvalue(),
        file_name=f"transacoes_{date_from}_{date_to}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ----- editar transacao (S18-T02) -----


def _tx_label(tx: dict) -> str:
    return f"{tx['date']} | {tx.get('description') or '(sem descricao)'} | {tx['amount']}"


tx_by_id = {t["id"]: t for t in items}

st.subheader("Editar transacao")

edit_id = st.selectbox(
    "Transacao para editar",
    options=list(tx_by_id.keys()),
    format_func=lambda i: _tx_label(tx_by_id[i]),
    key="edit_tx_select",
)
current = tx_by_id[edit_id]
cur_type = current.get("type", "expense")

# Tipo fica FORA do form para filtrar categorias de forma reativa (S26-T03).
# A key inclui edit_id para reinicializar ao trocar a transacao selecionada.
ed_type = st.radio(
    "Tipo",
    options=["income", "expense"],
    index=0 if cur_type == "income" else 1,
    horizontal=True,
    format_func=lambda v: "Receita" if v == "income" else "Despesa",
    key=f"edit_tx_type_{edit_id}",
)
ed_cats = filter_categories_by_type(categories, ed_type)
if not ed_cats:
    # fallback: usa todas as categorias se nenhuma do tipo for encontrada
    ed_cats = list(categories)

try:
    cur_date = datetime.fromisoformat(current["date"]).date()
except (TypeError, ValueError):
    cur_date = date.today()

cur_amount = float(current.get("amount", 0))
cur_account_id = current.get("account_id")
cur_category_id = current.get("category_id")
cur_payment = current.get("payment_method") or ""
cur_description = current.get("description") or ""
cur_recurring = bool(current.get("is_recurring", False))

submit_edit, edit_values = transaction_form(
    accounts=accounts,
    categories=ed_cats,
    type_value=ed_type,
    initial={
        "amount": cur_amount,
        "date": cur_date,
        "account_id": cur_account_id,
        "category_id": cur_category_id,
        "description": cur_description,
        "payment_method": cur_payment,
        "is_recurring": cur_recurring,
    },
    submit_label="Salvar",
    form_key=f"form_editar_transacao_{edit_id}",
)

if submit_edit and edit_values is not None:
    try:
        transactions_service.update_transaction(
            token, edit_id, base_url=api_base, **edit_values
        )
        st.success("Transacao atualizada")
        st.rerun()
    except api.ApiError as e:
        st.error(e.detail)


# ----- excluir transacao (S18-T03) -----

st.subheader("Excluir transacao")

del_id = st.selectbox(
    "Transacao para excluir",
    options=list(tx_by_id.keys()),
    format_func=lambda i: _tx_label(tx_by_id[i]),
    key="delete_tx_select",
)

confirmado = st.checkbox(
    "Confirmo a exclusao — esta acao nao pode ser desfeita",
    key="confirm_delete_tx",
)

if st.button("Excluir", type="primary", disabled=not confirmado, key="btn_delete_tx"):
    try:
        transactions_service.delete_transaction(token, int(del_id), base_url=api_base)
        st.success("Transacao excluida")
        st.rerun()
    except api.ApiError as e:
        st.error(e.detail)
