"""Entrypoint FastAPI. /health y /metrics públicos (las convenciones internas de API §1); todo lo demás
vive en app.api con su propia auth por dependencia.

Acá también viven los exception handlers que fuerzan el envelope de error de
las convenciones internas de API §1 (`{"error": {"code", "message"}}`): FastAPI por defecto envuelve el
`detail` de una HTTPException en `{"detail": ...}`, que no es lo que el contrato pide.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import router as api_router
from app.settings import settings

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(settings.service_name)

app = FastAPI(title="fraud-scoring")
app.include_router(api_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Los HTTPException que levantamos nosotros (app.auth) ya traen detail con la forma
    # del contrato; cualquier otra (404 de una ruta que no existe, etc.) se envuelve acá.
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        body = detail
    else:
        body = {"error": {"code": "http_error", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = errors[0]["msg"] if errors else "request inválido"
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": message}},
    )


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
