"""Configuracao de logging (S01-T05).

Em production/staging: JSON (machine-friendly). Em development/test:
texto colorido-ish (humano). Sempre inclui o atributo `request_id`
quando presente no LogRecord (extra={"request_id": ...}).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

JSON_ENVIRONMENTS = {"production", "staging"}


class JsonFormatter(logging.Formatter):
    """Formata o LogRecord como uma unica linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)-7s %(name)s [rid=%(request_id)s] %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


def configure_logging(environment: str) -> None:
    """Configura o root logger conforme o ambiente.

    Idempotente: chamadas repetidas substituem os handlers existentes.
    """
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if environment in JSON_ENVIRONMENTS:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root.addHandler(handler)
    root.setLevel(logging.INFO)
