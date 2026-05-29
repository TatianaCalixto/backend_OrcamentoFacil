"""Testes do import CSV no wrapper api.py (S18-T04).

Mocka requests.* para nao depender de backend rodando.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PANEL_DIR = Path(__file__).resolve().parent.parent
if str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))

import api  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> object:
        return self._payload


def test_import_csv_envia_multipart_correto() -> None:
    fake = _FakeResponse(200, {"imported": 0, "failed": 0, "errors": []})
    with patch("api.requests.post", return_value=fake) as mock_post:
        api.import_csv(
            "tok",
            account_id=42,
            file_name="transacoes.csv",
            file_bytes=b"data,description,amount\n",
            base_url="http://b",
        )
    args, kwargs = mock_post.call_args
    assert args[0] == "http://b/imports/csv"
    # multipart files: deve ser tupla (filename, bytes, mimetype)
    files = kwargs["files"]
    assert "file" in files
    fname, fbytes, mimetype = files["file"]
    assert fname == "transacoes.csv"
    assert fbytes == b"data,description,amount\n"
    assert mimetype == "text/csv"
    # account_id vai no form data, nao no json
    assert kwargs["data"] == {"account_id": 42}
    assert "json" not in kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer tok"


def test_import_csv_retorna_resumo_com_erros_parciais() -> None:
    payload = {
        "imported": 3,
        "failed": 2,
        "errors": [
            {"row": 5, "message": "valor invalido"},
            {"row": 9, "message": "categoria desconhecida"},
        ],
    }
    fake = _FakeResponse(200, payload)
    with patch("api.requests.post", return_value=fake):
        result = api.import_csv(
            "tok",
            account_id=1,
            file_name="x.csv",
            file_bytes=b"x",
            base_url="http://b",
        )
    assert result["imported"] == 3
    assert result["failed"] == 2
    assert len(result["errors"]) == 2
    assert result["errors"][0]["row"] == 5


def test_import_csv_erro_400_levanta_api_error() -> None:
    fake = _FakeResponse(400, {"detail": "arquivo invalido"})
    with patch("api.requests.post", return_value=fake):
        with pytest.raises(api.ApiError) as exc_info:
            api.import_csv(
                "tok",
                account_id=1,
                file_name="x.csv",
                file_bytes=b"x",
                base_url="http://b",
            )
    assert exc_info.value.status_code == 400
    assert "invalido" in exc_info.value.detail
