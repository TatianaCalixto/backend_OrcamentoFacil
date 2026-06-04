"""Formato e idioma (PT-BR) das mensagens de erro principais (S24-T05).

Valida o envelope padronizado {detail, code, request_id} + header X-Request-ID,
e que as mensagens das falhas principais estao em PT-BR (com acento) e sem
mistura pt/en. Convencao documentada em docs/PADROES.md.
"""

from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except (ValueError, TypeError):
        return False


def _auth(email: str = "err@ex.com") -> dict[str, str]:
    client.post("/auth/register", json={"name": "E", "email": email, "password": "Senha123"})
    r = client.post("/auth/login", json={"email": email, "password": "Senha123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_envelope_padronizado_no_401() -> None:
    """Formato: detail/code/request_id + header X-Request-ID correlacionado."""
    r = client.get("/accounts")  # sem token
    assert r.status_code == 401
    body = r.json()
    assert set(body) == {"detail", "code", "request_id"}
    assert body["detail"] == "não autenticado"
    assert body["code"] == "http_401"
    assert _is_uuid(body["request_id"])
    assert r.headers.get("X-Request-ID") == body["request_id"]


@pytest.mark.parametrize(
    ("caminho", "detail_esperado"),
    [
        ("/accounts/999999", "conta não encontrada"),
        ("/transactions/999999", "transação não encontrada"),
        ("/budgets/999999", "orçamento não encontrado"),
        ("/goals/999999", "meta não encontrada"),
        ("/categories/999999", "categoria não encontrada"),
    ],
)
def test_mensagens_404_canonicas_pt_br(caminho: str, detail_esperado: str) -> None:
    r = client.get(caminho, headers=_auth())
    assert r.status_code == 404, r.text
    body = r.json()
    assert body["detail"] == detail_esperado
    assert body["code"] == "http_404"


def test_email_duplicado_409_pt_br() -> None:
    client.post("/auth/register", json={"name": "D", "email": "dup@ex.com", "password": "Senha123"})
    r = client.post(
        "/auth/register", json={"name": "D", "email": "dup@ex.com", "password": "Senha123"}
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "email já cadastrado"


def test_credenciais_invalidas_401_pt_br() -> None:
    r = client.post("/auth/login", json={"email": "naoexiste@ex.com", "password": "Senha123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "credenciais inválidas"


def test_validacao_422_usa_code_padrao() -> None:
    r = client.post(
        "/auth/register", json={"name": "X", "email": "x@ex.com", "password": "abcdefgh"}
    )
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"
    assert "número" in r.text.lower()  # mensagem PT-BR (com acento) chegou no corpo


# termos em ingles que NAO devem aparecer em mensagens (tem traducao obvia em PT)
_TERMOS_EN = re.compile(
    r"\b(account|category|budget|color|header|invalid|not found|internal server)\b",
    re.IGNORECASE,
)


def test_mensagens_principais_nao_misturam_ingles() -> None:
    h = _auth("scan@ex.com")
    detalhes = [
        client.get("/accounts").json()["detail"],  # 401
        client.post("/auth/login", json={"email": "x@ex.com", "password": "errada1"}).json()[
            "detail"
        ],  # 401 credenciais
    ]
    for caminho in (
        "/accounts/999999",
        "/transactions/999999",
        "/budgets/999999",
        "/goals/999999",
        "/categories/999999",
    ):
        detalhes.append(client.get(caminho, headers=h).json()["detail"])

    for d in detalhes:
        assert isinstance(d, str)
        assert not _TERMOS_EN.search(d), f"mensagem contém termo em inglês: {d!r}"
