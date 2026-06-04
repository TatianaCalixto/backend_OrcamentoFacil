"""Service de categorias (S26-T01).

O painel apenas LISTA categorias (não há mutação de categoria no painel), então
expõe `list_categories` cacheado por 60s. `clear_cache()` permite invalidar
manualmente se necessário.
"""

from __future__ import annotations

import streamlit as st

import api


@st.cache_data(ttl=60)
def list_categories(token: str, base_url: str = api.DEFAULT_BASE_URL) -> list[dict]:
    return api.list_categories(token, base_url=base_url)


def clear_cache() -> None:
    list_categories.clear()
