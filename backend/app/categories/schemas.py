"""Schemas Pydantic para Category (S04-T03)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.categories.models import CategoryType

_HEX_COLOR_LEN = 7  # "#rrggbb"


def _validate_hex_color(v: str) -> str:
    v = v.strip()
    if len(v) != _HEX_COLOR_LEN or not v.startswith("#"):
        raise ValueError("color deve estar no formato #rrggbb")
    try:
        int(v[1:], 16)
    except ValueError as e:
        raise ValueError("color deve ser hexadecimal valido") from e
    return v.lower()


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    type: CategoryType
    color: str = Field(default="#888888")
    icon: str = Field(default="circle", min_length=1, max_length=40)

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        return _validate_hex_color(v)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    type: CategoryType | None = None
    color: str | None = None
    icon: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("color")
    @classmethod
    def _color(cls, v: str | None) -> str | None:
        return _validate_hex_color(v) if v is not None else None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    type: CategoryType
    color: str
    icon: str
    is_default: bool
