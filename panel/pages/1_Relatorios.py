"""Relatorios mensais e por categoria (S15-T02)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import api

st.set_page_config(page_title="Relatorios — OrcaFacil", layout="wide")


def _require_auth() -> tuple[str, str]:
    if "token" not in st.session_state:
        st.warning("Faca login na pagina principal para acessar os relatorios.")
        st.stop()
    return st.session_state["token"], st.session_state.get("api_base", api.DEFAULT_BASE_URL)


token, api_base = _require_auth()

st.title("Relatorios financeiros")

# ----- filtros globais -----
today = date.today()
col_m, col_y = st.columns(2)
with col_m:
    month = st.selectbox(
        "Mes", options=list(range(1, 13)), index=today.month - 1, format_func=lambda i: f"{i:02d}"
    )
with col_y:
    year = st.number_input("Ano", value=today.year, min_value=2000, max_value=2100, step=1)

# ----- Resumo mensal -----
st.header("Resumo mensal")
try:
    summary = api.monthly_summary(token, int(month), int(year), base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar resumo: {e.detail}")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Receita total", f"R$ {summary['receita_total']}")
c2.metric("Despesa total", f"R$ {summary['despesa_total']}")
c3.metric("Saldo do mes", f"R$ {summary['saldo']}")

st.subheader("Contas")
if summary["contas"]:
    contas_df = pd.DataFrame(summary["contas"])
    contas_df["current_balance"] = contas_df["current_balance"].astype(float)
    st.dataframe(contas_df, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma conta cadastrada.")

# ----- Breakdown por categoria -----
st.header("Despesas por categoria")
try:
    breakdown = api.category_breakdown(token, int(month), int(year), base_url=api_base)
except api.ApiError as e:
    st.error(f"Erro ao carregar breakdown: {e.detail}")
else:
    items = breakdown["items"]
    if items:
        bd_df = pd.DataFrame(items)
        bd_df["total"] = bd_df["total"].astype(float)
        fig = px.pie(
            bd_df, values="total", names="name",
            color="name",
            color_discrete_map=dict(zip(bd_df["name"], bd_df["color"], strict=False)),
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(bd_df[["name", "total"]], use_container_width=True, hide_index=True)
    else:
        st.info("Sem despesas no mes selecionado.")

# ----- Fluxo de caixa -----
st.header("Fluxo de caixa")
default_from = today.replace(day=1) - timedelta(days=30)
col_f1, col_f2 = st.columns(2)
with col_f1:
    date_from = st.date_input("De", value=default_from)
with col_f2:
    date_to = st.date_input("Ate", value=today)

if date_from > date_to:
    st.error("Data inicial maior que a final.")
else:
    try:
        cf = api.cashflow(token, date_from.isoformat(), date_to.isoformat(), base_url=api_base)
    except api.ApiError as e:
        st.error(f"Erro ao carregar fluxo: {e.detail}")
    else:
        pts = cf["points"]
        if pts:
            cf_df = pd.DataFrame(pts)
            cf_df["date"] = pd.to_datetime(cf_df["date"])
            for col in ("receita", "despesa", "saldo_acumulado"):
                cf_df[col] = cf_df[col].astype(float)
            fig = px.line(
                cf_df, x="date", y="saldo_acumulado",
                title="Saldo acumulado no periodo",
                markers=True,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(cf_df, use_container_width=True, hide_index=True)
        else:
            st.info("Sem movimentacoes no periodo selecionado.")
