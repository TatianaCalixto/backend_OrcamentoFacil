"""Configuracao de logging (S01-T05).

Em production/staging: JSON (machine-friendly). Em development/test:
texto colorido-ish (humano). Sempre inclui o atributo `request_id`
quando presente no LogRecord (extra={"request_id": ...}).
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import urllib.request
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


class LogShippingHandler(logging.Handler):
    """Envia cada LogRecord como JSON via POST a um agregador externo (S21-T03).

    Ativo apenas quando url e token estao configurados; caso contrario nem e
    adicionado (ver configure_logging). Erros de envio sao engolidos
    (handleError) — logging nunca deve derrubar a aplicacao. Uma guarda de
    re-entrancia evita recursao caso o proprio envio gere logs.

    Nota: envio sincrono por registro (timeout curto). Para alto volume em
    producao, evoluir para envio em lote/assincrono (fila + worker).
    """

    def __init__(self, url: str, token: str, *, timeout: float = 2.0) -> None:
        super().__init__()
        self.url = url
        self.token = token
        self.timeout = timeout
        self.setFormatter(JsonFormatter())
        self._local = threading.local()

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(self._local, "sending", False):
            return  # evita recursao (logs emitidos durante o proprio envio)
        self._local.sending = True
        try:
            body = self.format(record).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}",
                },
            )
            urllib.request.urlopen(req, timeout=self.timeout)  # noqa: S310 (url e de config)
        except Exception:
            self.handleError(record)
        finally:
            self._local.sending = False


def configure_logging(
    environment: str,
    *,
    log_shipping_url: str | None = None,
    log_shipping_token: str | None = None,
) -> None:
    """Configura o root logger conforme o ambiente.

    Idempotente: chamadas repetidas substituem os handlers existentes. Quando
    log_shipping_url e log_shipping_token estao definidos, adiciona tambem o
    LogShippingHandler (envio ao agregador externo); senao, apenas stdout.
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

    if log_shipping_url and log_shipping_token:
        root.addHandler(LogShippingHandler(log_shipping_url, log_shipping_token))

    root.setLevel(logging.INFO)
