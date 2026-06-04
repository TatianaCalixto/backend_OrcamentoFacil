"""Schemas Pydantic para User (S02-T04)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    # min_length fica a cargo do validator para dar mensagem clara em PT (S20-T06).
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("email inválido")
        return v

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, v: str) -> str:
        """Politica de senha forte (S20-T06): >=8 chars, >=1 letra e >=1 numero."""
        if len(v) < 8:
            raise ValueError("senha deve ter no mínimo 8 caracteres")
        if not any(c.isalpha() for c in v):
            raise ValueError("senha deve conter ao menos 1 letra")
        if not any(c.isdigit() for c in v):
            raise ValueError("senha deve conter ao menos 1 número")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
