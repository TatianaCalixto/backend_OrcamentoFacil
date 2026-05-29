"""Aplicacao FastAPI do OrcaFacil.

S01-T01 entregou a estrutura base. S01-T05 acopla logging estruturado,
middleware de request_id e exception handlers padronizados (HTTPException,
RequestValidationError e Exception generica). Sprint 10 adiciona CORS por
ambiente, rate limiting, refresh token e polish do OpenAPI.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.accounts.router import router as accounts_router
from app.auth.router import router as auth_router
from app.budgets.router import router as budgets_router
from app.categories.router import router as categories_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.ratelimit import limiter, rate_limit_exceeded_handler
from app.core.security_headers import SecurityHeadersMiddleware
from app.dashboard.router import router as dashboard_router
from app.goals.router import router as goals_router
from app.imports.router import router as imports_router
from app.transactions.router import router as transactions_router
from app.users.router import router as users_router

_settings = get_settings()
configure_logging(
    _settings.environment,
    log_shipping_url=_settings.log_shipping_url,
    log_shipping_token=_settings.log_shipping_token,
)
logger = logging.getLogger("orcafacil")

app = FastAPI(
    title="OrçaFácil API",
    version=__version__,
    description=(
        "API do OrçaFácil — controle financeiro pessoal. "
        "Auth JWT (access + refresh), CRUD de contas, categorias, transações, "
        "orçamentos e metas, agregações de dashboard e import CSV de extratos."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Autenticação (register, login, refresh)."},
        {"name": "users", "description": "Usuário corrente."},
        {"name": "accounts", "description": "Contas financeiras."},
        {"name": "categories", "description": "Categorias de receita/despesa."},
        {"name": "transactions", "description": "Lançamentos financeiros."},
        {"name": "budgets", "description": "Orçamentos mensais por categoria."},
        {"name": "goals", "description": "Metas financeiras."},
        {"name": "dashboard", "description": "Agregações para dashboard."},
        {"name": "imports", "description": "Import CSV de extratos."},
    ],
)

# rate limit: registra limiter e handler de 429 (com Retry-After)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# headers de seguranca HTTP (S20-T04); HSTS apenas em producao
app.add_middleware(
    SecurityHeadersMiddleware,
    production=_settings.environment == "production",
)

register_error_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(goals_router)
app.include_router(dashboard_router)
app.include_router(imports_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
