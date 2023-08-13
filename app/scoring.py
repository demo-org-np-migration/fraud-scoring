"""Fórmula de scoring. Documentada en detalle en notebooks/umbrales.md.

score = 0.6 * vendor.risk + 0.4 * min(velocity / 10, 1)

Umbrales:
- score >= 0.85 -> reject
- score >= 0.6  -> review
- score <  0.6  -> approve

`signals` es una lista human-readable para que backoffice pueda mostrar por qué se
tomó la decisión sin ir a buscar los números crudos.
"""
from __future__ import annotations

from dataclasses import dataclass

REJECT_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.6
VELOCITY_CAP = 10


@dataclass(frozen=True)
class ScoreResult:
    score: float
    decision: str
    signals: list[str]


def compute_score(*, vendor_risk: float, velocity_count: int) -> ScoreResult:
    velocity_component = min(velocity_count / VELOCITY_CAP, 1.0)
    score = round(0.6 * vendor_risk + 0.4 * velocity_component, 3)

    if score >= REJECT_THRESHOLD:
        decision = "reject"
    elif score >= REVIEW_THRESHOLD:
        decision = "review"
    else:
        decision = "approve"

    signals = [f"velocity:{velocity_count}", f"sentinel:{vendor_risk}"]
    return ScoreResult(score=score, decision=decision, signals=signals)


def list_rules() -> list[dict]:
    """Usado por GET /v1/rules. Refleja las mismas constantes de arriba a propósito:
    si se tocan los umbrales, esto se actualiza solo."""
    return [
        {"name": "reject", "threshold": REJECT_THRESHOLD},
        {"name": "review", "threshold": REVIEW_THRESHOLD},
    ]
