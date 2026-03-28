from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class ParsedAddress(BaseModel):
    house_number: str
    street_name: str
    borough: str


class RiskProfile(BaseModel):
    score: int
    caution_level: str  # "High", "Moderate", "Low"
    reasons: list[str]


class BuildingContext(BaseModel):
    violations: list[dict]
    complaints: list[dict]
    litigations: list[dict]
    risk_profile: RiskProfile


class AnalyzeResponse(BaseModel):
    session_id: str
    address: ParsedAddress
    violations: list[dict]
    complaints: list[dict]
    litigations: list[dict]
    risk_profile: RiskProfile
    summary: str
    data_warning: bool = False


class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: BuildingContext


class ChatResponse(BaseModel):
    reply: str
    session_id: str
