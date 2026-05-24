"""Rate limiting (S10-T02). slowapi com chave por IP."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter unico, importado em main.py para registrar handler e em routers
# que aplicam limites. enabled=True por padrao; testes podem desabilitar
# via limiter.enabled = False.
limiter = Limiter(key_func=get_remote_address, default_limits=[])
