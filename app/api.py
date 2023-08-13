"""Rutas HTTP de negocio (las convenciones internas de API §6 fraud-scoring).

POST /v1/score  -> service role
GET  /v1/rules  -> cualquier JWT válido
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_service_role, require_token
from app.scoring import compute_score, list_rules
from app.sentinel import sentinel_client
from app.velocity import bump_velocity

router = APIRouter(prefix="/v1")


class ScoreRequest(BaseModel):
    payment_id: str
    from_account: str
    to_account: str
    amount: str
    currency: str = Field(min_length=3, max_length=3)


class ScoreResponse(BaseModel):
    score: float
    decision: str
    signals: list[str]


@router.post("/score", response_model=ScoreResponse, status_code=200)
async def score_payment(body: ScoreRequest, _claims: dict = Depends(require_service_role)) -> ScoreResponse:
    velocity_count = await bump_velocity(body.from_account)
    vendor_result = await sentinel_client.assess(
        amount=body.amount,
        currency=body.currency,
        from_account=body.from_account,
        to_account=body.to_account,
    )
    vendor_risk = float(vendor_result.get("risk", 0.0))

    result = compute_score(vendor_risk=vendor_risk, velocity_count=velocity_count)
    return ScoreResponse(score=result.score, decision=result.decision, signals=result.signals)


@router.get("/rules")
async def get_rules(_claims: dict = Depends(require_token)) -> list[dict]:
    return list_rules()
