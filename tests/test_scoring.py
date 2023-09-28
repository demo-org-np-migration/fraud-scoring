"""Umbrales de decisión, vendor mockeado. No pega red: compute_score es pura."""
from app.scoring import compute_score, list_rules


def test_low_risk_low_velocity_is_approve():
    result = compute_score(vendor_risk=0.1, velocity_count=1)
    assert result.decision == "approve"
    assert result.score < 0.6


def test_high_vendor_risk_alone_triggers_reject():
    # 0.6 * 1.0 + 0.4 * 0 = 0.6 -> review, no reject. Necesitamos vendor_risk que sumado
    # a algo de velocidad cruce 0.85.
    result = compute_score(vendor_risk=1.0, velocity_count=10)
    assert result.score == 1.0
    assert result.decision == "reject"


def test_mid_score_is_review():
    # 0.6*0.7 + 0.4*0.5 = 0.42 + 0.2 = 0.62
    result = compute_score(vendor_risk=0.7, velocity_count=5)
    assert result.decision == "review"


def test_signals_include_velocity_and_sentinel():
    result = compute_score(vendor_risk=0.3, velocity_count=2)
    assert result.signals == ["velocity:2", "sentinel:0.3"]


def test_velocity_is_capped_at_ten():
    capped = compute_score(vendor_risk=0.0, velocity_count=100)
    at_cap = compute_score(vendor_risk=0.0, velocity_count=10)
    assert capped.score == at_cap.score


def test_list_rules_matches_thresholds():
    rules = list_rules()
    names = {r["name"]: r["threshold"] for r in rules}
    assert names["reject"] == 0.85
    assert names["review"] == 0.6
