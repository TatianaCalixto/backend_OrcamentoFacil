"""Testes da carga de Settings (S01-T02)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _make_env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    """Limpa env e injeta apenas os valores informados."""
    for key in (
        "DATABASE_URL",
        "JWT_SECRET",
        "JWT_ALGORITHM",
        "JWT_EXPIRE_MINUTES",
        "ENVIRONMENT",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_settings_le_valores_do_ambiente(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _make_env(
        monkeypatch,
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/db",
        JWT_SECRET="segredo_de_teste",
        JWT_ALGORITHM="HS512",
        JWT_EXPIRE_MINUTES="30",
        ENVIRONMENT="test",
    )
    monkeypatch.chdir(tmp_path)  # garante que nao acha .env real
    s = Settings()

    assert s.database_url == "postgresql+psycopg://u:p@localhost:5432/db"
    assert s.jwt_secret == "segredo_de_teste"
    assert s.jwt_algorithm == "HS512"
    assert s.jwt_expire_minutes == 30
    assert s.environment == "test"


def test_settings_usa_defaults_quando_opcionais_ausentes(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _make_env(
        monkeypatch,
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/db",
        JWT_SECRET="segredo_de_teste",
    )
    monkeypatch.chdir(tmp_path)
    s = Settings()

    assert s.jwt_algorithm == "HS256"
    assert s.jwt_expire_minutes == 60
    assert s.environment == "development"


def test_settings_falha_quando_obrigatoria_ausente(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _make_env(monkeypatch, JWT_SECRET="segredo")  # falta DATABASE_URL
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "DATABASE_URL" in str(exc_info.value)


def test_settings_rejeita_environment_invalido(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _make_env(
        monkeypatch,
        DATABASE_URL="postgresql+psycopg://u:p@localhost:5432/db",
        JWT_SECRET="s",
        ENVIRONMENT="hacker",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        Settings()
