"""Smoke tests de producao (S16-T06).

Roda contra a URL apontada por ORCAFACIL_SMOKE_URL (default
http://localhost:8000) e valida endpoints criticos SEM destruir dados:

  1. GET /health -> 200, body {status:"ok", version:...}
  2. POST /auth/register com email aleatorio -> 201
  3. POST /auth/login -> 200, retorna access_token e refresh_token
  4. GET /users/me com token -> 200
  5. GET /accounts -> 200 (lista pode estar vazia)
  6. GET /categories -> 200 com >= 8 itens (seed default)
  7. GET /dashboard/monthly-summary -> 200
  8. POST /auth/refresh -> 200, novo par de tokens

Uso:
    ORCAFACIL_SMOKE_URL=https://meu-deploy.com python scripts/smoke_prod.py

Saida: prints com status de cada passo. Codigo de retorno 0 se tudo
verde, 1 se qualquer asserticao falhar.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date

import requests

URL = os.environ.get("ORCAFACIL_SMOKE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 15


class SmokeFailure(Exception):
    pass


def _check(condition: bool, msg: str) -> None:
    if not condition:
        raise SmokeFailure(msg)


def smoke() -> None:
    print(f"=== OrcaFacil smoke contra {URL} ===")

    # 1. health
    r = requests.get(f"{URL}/health", timeout=TIMEOUT)
    _check(r.status_code == 200, f"/health status {r.status_code}")
    body = r.json()
    _check(body.get("status") == "ok", f"/health body {body}")
    print(f"[OK] /health  version={body.get('version')}")

    # 2. register
    suffix = uuid.uuid4().hex[:8]
    email = f"smoke_{suffix}@example.com"
    password = "smoke_password_123"
    r = requests.post(
        f"{URL}/auth/register",
        json={"name": f"Smoke {suffix}", "email": email, "password": password},
        timeout=TIMEOUT,
    )
    _check(r.status_code == 201, f"/auth/register status {r.status_code}: {r.text}")
    user_id = r.json()["id"]
    print(f"[OK] /auth/register  user_id={user_id} email={email}")

    # 3. login
    r = requests.post(
        f"{URL}/auth/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    _check(r.status_code == 200, f"/auth/login status {r.status_code}: {r.text}")
    tokens = r.json()
    access = tokens["access_token"]
    refresh = tokens.get("refresh_token")
    _check(bool(access), "login sem access_token")
    _check(bool(refresh), "login sem refresh_token")
    print("[OK] /auth/login  recebeu access + refresh")

    h = {"Authorization": f"Bearer {access}"}

    # 4. me
    r = requests.get(f"{URL}/users/me", headers=h, timeout=TIMEOUT)
    _check(r.status_code == 200, f"/users/me status {r.status_code}")
    _check(r.json()["email"] == email, "email de /me nao bate")
    print("[OK] /users/me")

    # 5. accounts
    r = requests.get(f"{URL}/accounts", headers=h, timeout=TIMEOUT)
    _check(r.status_code == 200, f"/accounts status {r.status_code}")
    print(f"[OK] /accounts  total={len(r.json())}")

    # 6. categories (>= 8 do seed default)
    r = requests.get(f"{URL}/categories", headers=h, timeout=TIMEOUT)
    _check(r.status_code == 200, f"/categories status {r.status_code}")
    cats = r.json()
    _check(
        len(cats) >= 8,
        f"/categories tem {len(cats)} (esperado >= 8 do seed)",
    )
    print(f"[OK] /categories  total={len(cats)}")

    # 7. dashboard monthly
    today = date.today()
    r = requests.get(
        f"{URL}/dashboard/monthly-summary",
        params={"month": today.month, "year": today.year},
        headers=h,
        timeout=TIMEOUT,
    )
    _check(r.status_code == 200, f"/dashboard/monthly-summary status {r.status_code}")
    body = r.json()
    _check(body["month"] == today.month, "month no body nao bate")
    print(f"[OK] /dashboard/monthly-summary  saldo={body['saldo']}")

    # 8. refresh
    r = requests.post(
        f"{URL}/auth/refresh",
        json={"refresh_token": refresh},
        timeout=TIMEOUT,
    )
    _check(r.status_code == 200, f"/auth/refresh status {r.status_code}: {r.text}")
    new = r.json()
    _check(bool(new["access_token"]), "refresh nao devolveu novo access_token")
    print("[OK] /auth/refresh  novo par de tokens")

    print("\n=== TUDO VERDE ===")


def main() -> int:
    try:
        smoke()
        return 0
    except SmokeFailure as e:
        print(f"\n[FAIL] {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"\n[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
