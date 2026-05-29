"""Rate limiting (S10-T02; estendido por usuario em S20-T03).

A chave do limite e por usuario autenticado quando ha um access token valido
no header Authorization, caindo para o IP de origem caso contrario (ex.:
/auth/login e /auth/register, que sao anonimos). Assim cada usuario tem seu
proprio balde de requisicoes nas mutacoes, independente do IP compartilhado.
"""

from __future__ import annotations

import contextlib

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.auth.jwt import TokenError, decode_token


def user_or_ip_key(request: Request) -> str:
    """Chave do rate limit: 'user:<id>' se houver access token valido; senao IP.

    Decodifica o Bearer token diretamente (sem depender da resolucao de
    dependencias do FastAPI), tolerando ausencia/erro de token. Refresh tokens
    nao contam como identificacao de usuario aqui.
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            payload = decode_token(token)
            if payload.get("typ") != "refresh":
                sub = payload.get("sub")
                if sub and str(sub).isdigit():
                    return f"user:{sub}"
        except TokenError:
            pass
    return get_remote_address(request)


# Limiter unico, importado em main.py para registrar handler e em routers
# que aplicam limites. enabled=True por padrao; testes desabilitam via
# limiter.enabled = False (conftest) e reabilitam com a fixture rate_limit_active.
limiter = Limiter(key_func=user_or_ip_key, default_limits=[])


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler de 429 com header Retry-After (criterio S20-T03).

    O handler padrao do slowapi so adiciona Retry-After com headers_enabled=True,
    que por sua vez exigiria um parametro `response: Response` em cada endpoint
    limitado. Aqui derivamos o Retry-After da janela do limite estourado
    (ex.: '10/minute' -> 60s), com fallback de 60s.
    """
    retry_after = 60
    if isinstance(exc, RateLimitExceeded):
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            retry_after = int(exc.limit.limit.get_expiry())
    detail = getattr(exc, "detail", "rate limit exceeded")
    response = JSONResponse(
        status_code=429,
        content={"detail": f"limite de requisicoes excedido: {detail}"},
    )
    response.headers["Retry-After"] = str(retry_after)
    return response
