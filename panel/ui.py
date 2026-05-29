"""Helpers de UI compartilhados entre as paginas Streamlit (S18-T05)."""

from __future__ import annotations

from typing import Iterable

import streamlit as st


def render_header() -> None:
    """Cabecalho visual padrao do painel."""
    st.markdown("# 💰 OrçaFácil")
    st.caption("Controle financeiro pessoal")


def filter_categories_by_type(
    cats: Iterable[dict], type_: str | None
) -> list[dict]:
    """Filtra categorias pelo campo `type` (`income`/`expense`).

    Se `type_` for None ou vazio, retorna a lista inteira (apos materializar).
    Categorias sem campo `type` ou com tipo diferente sao excluidas quando
    `type_` for informado.
    """
    items = list(cats)
    if not type_:
        return items
    return [c for c in items if c.get("type") == type_]
