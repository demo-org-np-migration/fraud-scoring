"""Cliente del vendor antifraude Sentinel (las convenciones internas de API §3).

POST /v2/assess {amount, currency, from_account, to_account} -> {risk: 0..1, signals: []}

El host sale de SENTINEL_URL (env). Este cliente no decide sandbox vs live: eso lo fija
el overlay de Kustomize que arma el ConfigMap (ver deploy/overlays/{staging,prod}).
"""
from __future__ import annotations

import httpx

from app.settings import settings


class SentinelClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._base_url = (base_url or settings.sentinel_url).rstrip("/")
        self._api_key = api_key or settings.sentinel_api_key

    async def assess(self, *, amount: str, currency: str, from_account: str, to_account: str) -> dict:
        url = f"{self._base_url}/v2/assess"
        headers = {"X-Api-Key": self._api_key} if self._api_key else {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                url,
                json={
                    "amount": amount,
                    "currency": currency,
                    "from_account": from_account,
                    "to_account": to_account,
                },
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


sentinel_client = SentinelClient()
