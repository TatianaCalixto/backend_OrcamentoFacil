"""Painel OrcaFacil — entrada Streamlit (S15-T01).

Login na pagina principal; relatorios e exportacao em paginas separadas
(pasta `pages/`).

Rodar:
    cd panel
    pip install -r requirements.txt
    streamlit run app.py

Variaveis: ORCAFACIL_API_URL (default http://localhost:8000).
"""

from __future__ import annotations

import streamlit as st

import api
from ui import render_header

st.set_page_config(page_title="OrcaFacil", page_icon=":money_with_wings:", layout="wide")

render_header()


def _logout() -> None:
    for k in ("token", "refresh_token", "user", "api_base"):
        st.session_state.pop(k, None)
    st.rerun()


def _login_form() -> None:
    st.title("OrcaFacil — Painel")
    st.write("Entre com suas credenciais para acessar os relatorios.")
    with st.form("login"):
        api_base = st.text_input("API URL", value=api.DEFAULT_BASE_URL)
        email = st.text_input("E-mail")
        password = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar")
    if ok:
        if not email or not password:
            st.error("Informe e-mail e senha.")
            return
        try:
            tokens = api.login(email, password, base_url=api_base)
            user = api.me(tokens["access_token"], base_url=api_base)
        except api.ApiError as e:
            st.error(f"Falha no login: {e.detail}")
            return
        st.session_state["token"] = tokens["access_token"]
        st.session_state["refresh_token"] = tokens.get("refresh_token")
        st.session_state["user"] = user
        st.session_state["api_base"] = api_base
        st.rerun()


def _logged_home() -> None:
    user = st.session_state["user"]
    st.title(f"Bem-vindo(a), {user['name']}!")
    st.write("Use o menu lateral para navegar pelos relatorios e exportar dados.")
    st.divider()
    cols = st.columns(3)
    cols[0].metric("Usuario", user["email"])
    cols[1].metric("ID", user["id"])
    cols[2].button("Logout", on_click=_logout, type="primary")

    st.subheader("Paginas disponiveis")
    st.markdown(
        """
        - **Relatorios**: resumo mensal, breakdown por categoria, fluxo de caixa.
        - **Transacoes**: lista filtravel + exportacao CSV/XLSX.
        """
    )


def main() -> None:
    if "token" in st.session_state and "user" in st.session_state:
        _logged_home()
    else:
        _login_form()


if __name__ == "__main__":
    main()
