"""Aplicacao FastAPI do OrcaFacil.

S01-T01 entrega a estrutura base: instancia FastAPI, CORS, exception
handler global minimo e endpoint /health. O handler sera enriquecido em
S01-T05 (logging estruturado + payload padronizado com request_id).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
