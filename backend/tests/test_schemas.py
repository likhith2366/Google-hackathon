from app.models.schemas import (
    QueryRequest, ParsedAddress, RiskProfile,
    BuildingContext, AnalyzeResponse, ChatRequest, ChatResponse,
)


def test_query_request_requires_query():
    req = QueryRequest(query="123 Main St Brooklyn")
    assert req.query == "123 Main St Brooklyn"


def test_risk_profile_fields():
    rp = RiskProfile(score=6, caution_level="High", reasons=["2 Class C violations"])
    assert rp.score == 6
    assert rp.caution_level == "High"


def test_analyze_response_default_data_warning_false():
    addr = ParsedAddress(house_number="123", street_name="Main St", borough="Brooklyn")
    rp = RiskProfile(score=0, caution_level="Low", reasons=[])
    resp = AnalyzeResponse(
        session_id="abc",
        address=addr,
        violations=[],
        complaints=[],
        litigations=[],
        risk_profile=rp,
        summary="All clear.",
    )
    assert resp.data_warning is False


def test_chat_request_fields():
    addr = ParsedAddress(house_number="1", street_name="Broadway", borough="Manhattan")
    rp = RiskProfile(score=0, caution_level="Low", reasons=[])
    ctx = BuildingContext(violations=[], complaints=[], litigations=[], risk_profile=rp)
    req = ChatRequest(session_id="sess-1", message="Can I negotiate rent?", context=ctx)
    assert req.session_id == "sess-1"
