"""Fixtures e configuracao global do pytest.

Define os ENV minimos exigidos pelo Settings (S01-T02) ANTES que
qualquer modulo da app seja importado. Se o ambiente ja tiver
DATABASE_URL/JWT_SECRET definidos (caso do CI), os valores ja
existentes sao respeitados (setdefault).
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test_secret_change_me")
os.environ.setdefault("ENVIRONMENT", "test")
