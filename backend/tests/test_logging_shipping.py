"""Log shipping condicional ao agregador externo (S21-T03).

Com LOG_SHIPPING_URL+TOKEN: logs estruturados sao enviados via POST.
Sem as vars: comportamento atual preservado (so stdout).
"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import pytest

from app.core.logging import LogShippingHandler, configure_logging


@pytest.fixture(autouse=True)
def _restore_root_logging():
    """Snapshot/restore do root logger para nao vazar handlers entre testes."""
    root = logging.getLogger()
    saved = list(root.handlers)
    level = root.level
    yield
    root.handlers[:] = saved
    root.setLevel(level)


def _record(msg: str = "hello") -> logging.LogRecord:
    return logging.LogRecord("test", logging.INFO, __file__, 1, msg, None, None)


def test_handler_envia_post_com_token_e_json() -> None:
    h = LogShippingHandler("https://logs.example.com/ingest", "tok-123")
    with patch("app.core.logging.urllib.request.urlopen") as m:
        h.emit(_record("ola mundo"))
    assert m.call_count == 1
    req = m.call_args[0][0]
    assert req.full_url == "https://logs.example.com/ingest"
    assert req.get_header("Authorization") == "Bearer tok-123"
    body = json.loads(req.data.decode("utf-8"))
    assert body["msg"] == "ola mundo"
    assert body["level"] == "INFO"


def test_configure_com_vars_adiciona_shipping_handler() -> None:
    with patch("app.core.logging.urllib.request.urlopen") as m:
        configure_logging("test", log_shipping_url="https://x/y", log_shipping_token="t")
        shippers = [h for h in logging.getLogger().handlers if isinstance(h, LogShippingHandler)]
        assert len(shippers) == 1
        logging.getLogger("orcafacil").info("teste de envio")
    assert m.call_count >= 1  # o log foi enviado ao agregador


def test_configure_sem_vars_so_stdout() -> None:
    configure_logging("test")  # sem url/token
    handlers = logging.getLogger().handlers
    assert not any(isinstance(h, LogShippingHandler) for h in handlers)
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)


def test_envio_falho_nao_propaga() -> None:
    h = LogShippingHandler("https://logs.example.com/ingest", "tok")
    with (
        patch("app.core.logging.urllib.request.urlopen", side_effect=OSError("rede caiu")),
        patch.object(h, "handleError") as he,
    ):
        h.emit(_record())  # nao deve levantar
        assert he.called
