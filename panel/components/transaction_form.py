"""Formulário compartilhado de transação (S26-T03).

Usado pela página de criação (4_Nova_Transacao) e pela de edição
(2_Transacoes), garantindo campos e validações idênticos. O radio de "Tipo"
fica FORA do form (na página) para filtrar categorias de forma reativa; o tipo
selecionado e a lista de categorias já filtradas são passados como parâmetros.

Retorna `(submitted, values)`:
- `submitted` = True quando o botão do form foi acionado.
- `values` = dict pronto para o service (inclui `type`) quando válido; `None`
  quando a validação falhou (ex.: valor <= 0), caso em que o erro já foi exibido.
"""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any

import streamlit as st

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


def transaction_form(
    *,
    accounts: list[dict],
    categories: list[dict],
    type_value: str,
    initial: dict | None = None,
    submit_label: str = "Salvar",
    form_key: str = "transaction_form",
    clear_on_submit: bool = False,
) -> tuple[bool, dict | None]:
    initial = initial or {}
    acc_options = [a["id"] for a in accounts]
    cat_options = [c["id"] for c in categories]

    def _index(options: list, value: Any) -> int:
        try:
            return options.index(value)
        except (ValueError, TypeError):
            return 0

    def _pay_index() -> int:
        return _index(PAYMENT_OPTIONS, initial.get("payment_method") or "")

    with st.form(form_key, clear_on_submit=clear_on_submit):
        amount = st.number_input(
            "Valor",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=float(initial.get("amount", 0.0)),
        )
        when = st.date_input("Data", value=initial.get("date", date_cls.today()))
        acc_id = st.selectbox(
            "Conta",
            options=acc_options,
            index=_index(acc_options, initial.get("account_id")) if acc_options else 0,
            format_func=lambda i: next((a["name"] for a in accounts if a["id"] == i), str(i)),
        )
        cat_id = st.selectbox(
            "Categoria",
            options=cat_options,
            index=_index(cat_options, initial.get("category_id")) if cat_options else 0,
            format_func=lambda i: next((c["name"] for c in categories if c["id"] == i), str(i)),
        )
        description = st.text_input("Descricao (opcional)", value=initial.get("description") or "")
        payment = st.selectbox(
            "Forma de pagamento",
            options=PAYMENT_OPTIONS,
            index=_pay_index(),
            format_func=lambda v: PAYMENT_LABELS[v],
        )
        is_recurring = st.checkbox("Recorrente", value=bool(initial.get("is_recurring", False)))
        submitted = st.form_submit_button(submit_label)

    if not submitted:
        return False, None

    if amount <= 0:
        st.error("Informe um valor maior que zero.")
        return True, None

    return True, {
        "account_id": int(acc_id),
        "category_id": int(cat_id),
        "type": type_value,
        "amount": float(amount),
        "date": when.isoformat(),
        "description": description.strip() or None,
        "payment_method": payment or None,
        "is_recurring": bool(is_recurring),
    }
