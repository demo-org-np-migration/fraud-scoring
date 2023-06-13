"""Contador de velocidad en Redis (las convenciones internas de API §6 fraud-scoring).

`INCR velocity:<from_account>` con TTL de 600s (10 minutos). Redis es el único
almacenamiento del servicio: no hay base propia (ver specs/fraud-scoring.md).
"""
from __future__ import annotations

import redis.asyncio as redis

from app.settings import settings

VELOCITY_WINDOW_SECONDS = 600

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def bump_velocity(from_account: str, *, client: redis.Redis | None = None) -> int:
    """Incrementa el contador de la cuenta origen y (re)pone el TTL de la ventana."""
    r = client or get_redis_client()
    key = f"velocity:{from_account}"
    count = await r.incr(key)
    await r.expire(key, VELOCITY_WINDOW_SECONDS)
    return count
