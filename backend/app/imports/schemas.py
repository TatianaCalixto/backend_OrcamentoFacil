"""Schemas Pydantic do import CSV (Sprint 9)."""

from __future__ import annotations

from pydantic import BaseModel


class ImportError(BaseModel):
    line_number: int
    message: str


class ImportResult(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[ImportError]
