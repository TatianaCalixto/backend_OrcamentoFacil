"""Settings da aplicacao (S01-T02).

Le variaveis do .env via Pydantic-Settings. Variaveis obrigatorias sem
valor falham no boot com erro claro do Pydantic.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(..., alias="DATABASE_URL")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
