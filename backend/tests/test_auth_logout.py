"""Logout e revogacao de refresh token (S20-T05)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.auth.models import RevokedToken
from app.auth.revoked import cleanup_expired
from app.database.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _register_login(email: str) -> tuple[str, str, int]:
    r = client.post("/auth/register", json={"name": "U", "email": email, "password": "senha123"})
    uid = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "senha123"})
    j = r.json()
    return j["access_token"], j["refresh_token"], uid


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_fluxo_register_login_refresh_logout_refresh_401() -> None:
    access, refresh, _uid = _register_login("log@ex.com")
    # refresh funciona ANTES do logout
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 200
    # logout revoga ESTE refresh
    r = client.post("/auth/logout", headers=_h(access), json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["detail"] == "logout efetuado"
    # o mesmo refresh nao serve mais
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_logout_exige_autenticacao() -> None:
    _a, refresh, _uid = _register_login("noauth@ex.com")
    r = client.post("/auth/logout", json={"refresh_token": refresh})  # sem Bearer
    assert r.status_code == 401


def test_logout_sem_refresh_ativo_e_idempotente() -> None:
    access, _refresh, _uid = _register_login("sem@ex.com")
    r = client.post("/auth/logout", headers=_h(access), json={"refresh_token": "lixo.invalido"})
    assert r.status_code == 200
    assert "nenhum refresh" in r.json()["detail"]


def test_logout_refresh_de_outro_usuario_401() -> None:
    access_a, _ra, _ua = _register_login("dono@ex.com")
    _ab, refresh_b, _ub = _register_login("outro@ex.com")
    r = client.post("/auth/logout", headers=_h(access_a), json={"refresh_token": refresh_b})
    assert r.status_code == 401


def test_logout_duas_vezes_e_idempotente() -> None:
    access, refresh, _uid = _register_login("dup@ex.com")
    assert (
        client.post("/auth/logout", headers=_h(access), json={"refresh_token": refresh}).status_code
        == 200
    )
    # segunda vez: jti ja revogado, endpoint nao quebra
    r = client.post("/auth/logout", headers=_h(access), json={"refresh_token": refresh})
    assert r.status_code == 200


async def test_cleanup_remove_apenas_expirados() -> None:
    _a, _r, uid = _register_login("cln@ex.com")
    now = datetime.now(UTC)
    async with SessionLocal() as db:
        db.add(RevokedToken(jti="velho", user_id=uid, revoked_at=now - timedelta(days=30)))
        db.add(RevokedToken(jti="novo", user_id=uid, revoked_at=now))
        await db.commit()
        removed = await cleanup_expired(db, now=now)
        assert removed == 1
        assert await db.get(RevokedToken, "velho") is None
        assert await db.get(RevokedToken, "novo") is not None
