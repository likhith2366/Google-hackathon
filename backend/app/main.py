from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.constants import (
    RISK_SCORE_CLASS_B,
    RISK_SCORE_CLASS_C,
    RISK_SCORE_LITIGATION,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MODERATE,
)
from app.models.schemas import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    QueryRequest,
    RiskProfile,
)
from app.services.gemini_service import (
    chat as gemini_chat,
    extract_address,
    generate_summary,
)
from app.services.nyc_service import fetch_all

app = FastAPI(title="NYC Tenant Advocate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _compute_risk(violations: list[dict], litigations: list[dict]) -> RiskProfile:
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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: QueryRequest):
    address = await extract_address(request.query)
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Could not parse a valid NYC address from your query.",
        )

    data = await fetch_all(address.house_number, address.street_name, address.borough)
    risk_profile = _compute_risk(data["violations"], data["litigations"])

    summary, session_id = await generate_summary(
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
    )

    return AnalyzeResponse(
        session_id=session_id,
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
        summary=summary,
        data_warning=data.get("data_warning", False),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await gemini_chat(
            client_token=request.session_id,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChatResponse(reply=reply, session_id=request.session_id)
