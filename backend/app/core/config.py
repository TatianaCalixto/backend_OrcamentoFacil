"""Settings da aplicacao (S01-T02, S10-T01, S10-T03).

Le variaveis do .env via Pydantic-Settings. Variaveis obrigatorias sem
valor falham no boot com erro claro do Pydantic.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_cors() -> list[str]:
    """Defaults seguros por ambiente: tudo liberado em dev/test, vazio em prod."""
    return [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
    ]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- DB -----
    database_url: str = Field(..., alias="DATABASE_URL")

    # ----- JWT (access + refresh) -----
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    jwt_refresh_expire_minutes: int = Field(
        default=60 * 24 * 7, alias="JWT_REFRESH_EXPIRE_MINUTES"
    )  # 7 dias

    # ----- ambiente -----
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )

    # ----- Log shipping (S21-T03): agregador externo opcional -----
    # Quando ambos definidos, logs estruturados sao enviados via POST ao agregador
    # (Better Stack/Logtail/etc.). Ausentes -> comportamento atual (so stdout).
    log_shipping_url: str | None = Field(default=None, alias="LOG_SHIPPING_URL")
    log_shipping_token: str | None = Field(default=None, alias="LOG_SHIPPING_TOKEN")

    # ----- CORS (S10-T01): aceita CSV ("a,b") ou JSON ('["a","b"]') no env -----
    cors_origins: list[str] = Field(default_factory=_default_cors, alias="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        if v is None or v == "":
            return _default_cors()
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json

                return [str(x).strip() for x in json.loads(s) if str(x).strip()]
            return [item.strip() for item in s.split(",") if item.strip()]
        raise ValueError("CORS_ORIGINS invalido")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
