"""Politica de senha forte no UserCreate (S20-T06).

Unit tests do schema (vazia, curta, so letras, so numeros, forte) + 2 de
integracao no /auth/register (fraca -> 422 com mensagem util; forte -> 201).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.users.schemas import UserCreate

client = TestClient(app, raise_server_exceptions=False)


def _make(password: str) -> UserCreate:
    return UserCreate(name="U", email="u@ex.com", password=password)


def test_senha_vazia_rejeitada() -> None:
    with pytest.raises(ValidationError) as exc:
        _make("")
    assert "8 caracteres" in str(exc.value)


def test_senha_curta_rejeitada() -> None:
    with pytest.raises(ValidationError) as exc:
        _make("abc123")  # 6 chars
    assert "8 caracteres" in str(exc.value)


def test_senha_so_letras_rejeitada() -> None:
    with pytest.raises(ValidationError) as exc:
        _make("abcdefgh")  # 8 letras, sem numero
    assert "número" in str(exc.value)


def test_senha_so_numeros_rejeitada() -> None:
    with pytest.raises(ValidationError) as exc:
        _make("12345678")  # 8 numeros, sem letra
    assert "letra" in str(exc.value)


def test_senha_forte_aceita() -> None:
    u = _make("senha123")
    assert u.password == "senha123"


def test_register_senha_fraca_retorna_422_com_mensagem() -> None:
    r = client.post(
        "/auth/register",
        json={"name": "X", "email": "fraca@ex.com", "password": "abcdefgh"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"
    assert "número" in r.text.lower()  # mensagem util chegou no corpo


def test_register_senha_forte_cria_usuario() -> None:
    r = client.post(
        "/auth/register",
        json={"name": "X", "email": "forte@ex.com", "password": "senha123"},
    )
    assert r.status_code == 201, r.text
