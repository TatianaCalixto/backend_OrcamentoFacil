"""Middleware de headers de seguranca HTTP (S20-T04).

Injeta em toda resposta:
- Content-Security-Policy: default-src 'self'
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- X-Frame-Options: DENY

E, apenas quando ENVIRONMENT=production:
- Strict-Transport-Security: max-age=31536000; includeSubDomains

HSTS so vai em producao porque em dev/test o trafego costuma ser HTTP puro e o
header instruiria o browser a forcar HTTPS num host que nao o serve.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Headers presentes em qualquer ambiente.
BASE_SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
}

HSTS_HEADER = "Strict-Transport-Security"
HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona os headers de seguranca em todas as respostas.

    Usa setdefault para nao sobrescrever um header que algum endpoint tenha
    definido explicitamente.
    """

    def __init__(self, app: ASGIApp, *, production: bool = False) -> None:
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in BASE_SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if self.production:
            response.headers.setdefault(HSTS_HEADER, HSTS_VALUE)
        return response
