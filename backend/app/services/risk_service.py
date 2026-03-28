from app.core.constants import (
    RISK_SCORE_CLASS_B,
    RISK_SCORE_CLASS_C,
    RISK_SCORE_LITIGATION,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MODERATE,
)
from app.models.schemas import RiskProfile


def compute_risk(violations: list[dict], litigations: list[dict]) -> RiskProfile:
    score = 0
    reasons: list[str] = []

    class_c = [v for v in violations if v.get("class", "").upper() == "C"]
    class_b = [v for v in violations if v.get("class", "").upper() == "B"]

    if class_c:
        score += len(class_c) * RISK_SCORE_CLASS_C
        reasons.append(f"{len(class_c)} immediately hazardous (Class C) violation(s)")
    if class_b:
        score += len(class_b) * RISK_SCORE_CLASS_B
        reasons.append(f"{len(class_b)} hazardous (Class B) violation(s)")
    if litigations:
        score += RISK_SCORE_LITIGATION
        reasons.append(f"Landlord has {len(litigations)} litigation record(s)")

    if score >= RISK_THRESHOLD_HIGH:
        level = "High"
    elif score >= RISK_THRESHOLD_MODERATE:
        level = "Moderate"
    else:
        level = "Low"

    return RiskProfile(score=score, caution_level=level, reasons=reasons)
