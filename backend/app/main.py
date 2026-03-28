from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.routers.voice import router as voice_router
from app.models.schemas import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    QueryRequest,
)
from app.services.gemini_service import (
    chat as gemini_chat,
    extract_address,
    generate_summary,
)
from app.services.nyc_service import fetch_all
from app.services.risk_service import compute_risk

app = FastAPI(title="NYC Tenant Advocate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: QueryRequest):
    address = await extract_address(request.query)
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Could not parse a valid NYC address from your query.",
        )

    data = await fetch_all(address.house_number, address.street_name, address.borough)
    risk_profile = compute_risk(data["violations"], data["litigations"])

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
