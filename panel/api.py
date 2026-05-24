"""Wrapper minimo de chamadas a API do backend OrcaFacil (Sprint 15)."""

from __future__ import annotations

import os
from typing import Any

import requests

DEFAULT_BASE_URL = os.environ.get("ORCAFACIL_API_URL", "http://localhost:8000")


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def _headers(token: str | None) -> dict[str, str]:
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _check(r: requests.Response) -> Any:
    if r.status_code >= 400:
        try:
            body = r.json()
            detail = body.get("detail", body)
        except ValueError:
            detail = r.text
        raise ApiError(r.status_code, str(detail))
    if r.status_code == 204:
        return None
    return r.json()


# ----- auth -----


def login(email: str, password: str, base_url: str = DEFAULT_BASE_URL) -> dict[str, str]:
    r = requests.post(
        f"{base_url}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    return _check(r)


def me(token: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    r = requests.get(f"{base_url}/users/me", headers=_headers(token), timeout=10)
    return _check(r)


# ----- dashboard -----


def monthly_summary(token: str, month: int, year: int, base_url: str = DEFAULT_BASE_URL) -> dict:
    r = requests.get(
        f"{base_url}/dashboard/monthly-summary",
        params={"month": month, "year": year},
        headers=_headers(token),
        timeout=15,
    )
    return _check(r)


def category_breakdown(
    token: str, month: int, year: int, base_url: str = DEFAULT_BASE_URL
) -> dict:
    r = requests.get(
        f"{base_url}/dashboard/category-breakdown",
        params={"month": month, "year": year},
        headers=_headers(token),
        timeout=15,
    )
    return _check(r)


def cashflow(token: str, date_from: str, date_to: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    r = requests.get(
        f"{base_url}/dashboard/cashflow",
        params={"date_from": date_from, "date_to": date_to},
        headers=_headers(token),
        timeout=15,
    )
    return _check(r)


# ----- transactions -----


def list_transactions(
    token: str,
    *,
    page: int = 1,
    page_size: int = 100,
    date_from: str | None = None,
    date_to: str | None = None,
    type_: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    search: str | None = None,
    base_url: str = DEFAULT_BASE_URL,
) -> dict:
    params: dict[str, Any] = {"page": page, "page_size": page_size}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    if type_:
        params["type"] = type_
    if account_id is not None:
        params["account_id"] = account_id
    if category_id is not None:
        params["category_id"] = category_id
    if search:
        params["search"] = search
    r = requests.get(
        f"{base_url}/transactions",
        params=params,
        headers=_headers(token),
        timeout=30,
    )
    return _check(r)


def list_accounts(token: str, base_url: str = DEFAULT_BASE_URL) -> list[dict]:
    r = requests.get(f"{base_url}/accounts", headers=_headers(token), timeout=10)
    return _check(r)


def list_categories(token: str, base_url: str = DEFAULT_BASE_URL) -> list[dict]:
    r = requests.get(f"{base_url}/categories", headers=_headers(token), timeout=10)
    return _check(r)
