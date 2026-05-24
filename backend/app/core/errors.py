"""Middleware de request_id e exception handlers globais (S01-T05)."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("orcafacil")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Gera (ou propaga) um request_id por requisicao e o anexa em
    request.state.request_id e no header da resposta."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _payload(detail: object, code: str, request_id: str) -> dict:
    return {"detail": detail, "code": code, "request_id": request_id}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    rid = _get_request_id(request)
    logger.warning(
        "http_exception status=%s detail=%s",
        exc.status_code,
        exc.detail,
        extra={"request_id": rid},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_payload(exc.detail, f"http_{exc.status_code}", rid),
        headers={REQUEST_ID_HEADER: rid},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    rid = _get_request_id(request)
    logger.warning(
        "validation_error errors=%s",
        exc.errors(),
        extra={"request_id": rid},
    )
    return JSONResponse(
        status_code=422,
        content=_payload(jsonable_encoder(exc.errors()), "validation_error", rid),
        headers={REQUEST_ID_HEADER: rid},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = _get_request_id(request)
    logger.exception(
        "unhandled_exception path=%s",
        request.url.path,
        extra={"request_id": rid},
    )
    return JSONResponse(
        status_code=500,
        content=_payload("Internal Server Error", "internal_error", rid),
        headers={REQUEST_ID_HEADER: rid},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
