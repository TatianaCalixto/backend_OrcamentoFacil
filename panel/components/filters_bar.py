"""Barra de filtros reutilizável e parametrizável (S26-T05) com persistência
entre reruns/navegação (S26-T04).

`filters_bar(specs, state_key=...)` renderiza uma lista CONFIGURÁVEL de filtros
e persiste a seleção em `st.session_state[state_key]` (ex.: 'transactions_filters').
Os widgets usam `key` própria (o Streamlit mantém o estado entre reruns e ao
sair/voltar da página); na primeira renderização caem no default (fallback).

Cada item de `specs` é um dict:
- key: str            -> chave do filtro no dict de retorno/persistência
- label: str          -> rótulo do widget
- kind: 'date'|'select'|'text'
- default: Any        -> valor inicial (fallback)
- options: list       -> (apenas 'select') opções
- format_func: callable -> (opcional, 'select') formata o rótulo das opções
"""

from __future__ import annotations

from typing import Any

import streamlit as st


def merge_filters(persisted: dict | None, defaults: dict) -> dict:
    """Mescla filtros persistidos com os defaults — fallback por chave.

    Pura (sem Streamlit), para testar a semântica de persistência/fallback.
    """
    merged = dict(defaults)
    if persisted:
        for key in defaults:
            if key in persisted:
                merged[key] = persisted[key]
    return merged


def filters_bar(specs: list[dict], *, state_key: str, n_cols: int = 4) -> dict[str, Any]:
    defaults = {s["key"]: s.get("default") for s in specs}
    init = merge_filters(st.session_state.get(state_key), defaults)

    values: dict[str, Any] = {}
    n = max(1, min(n_cols, len(specs)))
    cols = st.columns(n)
    for i, spec in enumerate(specs):
        wkey = f"{state_key}__{spec['key']}"
        kind = spec["kind"]
        label = spec["label"]
        # inicializa o estado da widget a partir do default/persistido (uma vez).
        if wkey not in st.session_state:
            st.session_state[wkey] = init[spec["key"]]
        # guarda p/ select: se o valor persistido nao esta mais nas opcoes
        # (ex.: contas mudaram), volta ao default valido.
        if kind == "select":
            options = spec["options"]
            if st.session_state.get(wkey) not in options:
                fallback = init[spec["key"]]
                st.session_state[wkey] = (
                    fallback if fallback in options else (options[0] if options else None)
                )
        with cols[i % n]:
            if kind == "date":
                value = st.date_input(label, key=wkey)
            elif kind == "select":
                value = st.selectbox(
                    label,
                    options=spec["options"],
                    format_func=spec.get("format_func", str),
                    key=wkey,
                )
            elif kind == "text":
                value = st.text_input(label, key=wkey)
            else:
                raise ValueError(f"tipo de filtro desconhecido: {kind!r}")
        values[spec["key"]] = value

    st.session_state[state_key] = values
    return values
