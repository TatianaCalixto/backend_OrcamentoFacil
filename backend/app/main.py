"""Aplicacao FastAPI do OrcaFacil.

S01-T01 entregou a estrutura base. S01-T05 acopla logging estruturado,
middleware de request_id e exception handlers padronizados (HTTPException,
RequestValidationError e Exception generica).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.accounts.router import router as accounts_router
from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.users.router import router as users_router

_settings = get_settings()
configure_logging(_settings.environment)
logger = logging.getLogger("orcafacil")

app = FastAPI(
    title="OrçaFácil API",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(categories_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
