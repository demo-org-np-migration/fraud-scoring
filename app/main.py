"""Entrypoint FastAPI. /health y /metrics públicos (las convenciones internas de API §1); todo lo demás
vive en app.api con su propia auth por dependencia."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import router as api_router
from app.settings import settings

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(settings.service_name)

app = FastAPI(title="fraud-scoring")
app.include_router(api_router)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
