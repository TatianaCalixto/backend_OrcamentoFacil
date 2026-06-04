"""Middleware de Cache-Control para respostas GET (S25-T05).

Coordenacao backend+mobile: respostas a requisicoes GET com status 2xx recebem
`Cache-Control: private, max-age=30`, permitindo que o mobile cacheie a leitura
por uma janela curta.

Regras:
- aplica somente em GET com status 2xx;
- NAO aplica em metodos de mutacao (POST/PUT/PATCH/DELETE) nem em respostas
  fora do 2xx;
- EXCLUI observabilidade/health (`/health`, `/healthz`, `/metrics`), que devem
  ficar sempre frescos.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

GET_CACHE_MAX_AGE_SECONDS = 30
CACHE_CONTROL_VALUE = f"private, max-age={GET_CACHE_MAX_AGE_SECONDS}"

# Prefixos de caminhos de observabilidade/health que NUNCA recebem o header.
_EXCLUDED_PREFIXES = ("/health", "/healthz", "/metrics")


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona Cache-Control em respostas GET 2xx (exceto health/metrics)."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if (
            request.method == "GET"
            and 200 <= response.status_code < 300
            and not request.url.path.startswith(_EXCLUDED_PREFIXES)
        ):
            response.headers["Cache-Control"] = CACHE_CONTROL_VALUE
        return response
