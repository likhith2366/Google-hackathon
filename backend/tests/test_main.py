import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import ParsedAddress, RiskProfile

client = TestClient(app)

MOCK_ADDRESS = ParsedAddress(house_number="123", street_name="Main St", borough="Brooklyn")
MOCK_RISK = RiskProfile(score=4, caution_level="Moderate", reasons=["2 Class B violations"])
MOCK_DATA = {
    "violations": [{"class": "B"}],
    "complaints": [],
    "litigations": [],
    "data_warning": False,
}


def test_analyze_returns_200_with_session_id():
    with patch("app.main.extract_address", new=AsyncMock(return_value=MOCK_ADDRESS)), \
         patch("app.main.fetch_all", new=AsyncMock(return_value=MOCK_DATA)), \
         patch("app.main.generate_summary", new=AsyncMock(return_value=("Great building.", "sess-abc"))):

        resp = client.post("/analyze", json={"query": "123 Main St Brooklyn"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-abc"
    assert body["summary"] == "Great building."
    assert body["risk_profile"]["caution_level"] == "Moderate"


def test_analyze_returns_400_on_unparseable_address():
    with patch("app.main.extract_address", new=AsyncMock(return_value=None)):
        resp = client.post("/analyze", json={"query": "gibberish"})

    assert resp.status_code == 400
    assert "address" in resp.json()["detail"].lower()


def test_chat_returns_200_with_reply():
    mock_context = {
        "violations": [],
        "complaints": [],
        "litigations": [],
        "risk_profile": {"score": 0, "caution_level": "Low", "reasons": []},
    }
    with patch("app.main.gemini_chat", new=AsyncMock(return_value="You can negotiate.")):
        resp = client.post("/chat", json={
            "session_id": "sess-abc",
            "message": "Can I reduce rent?",
            "context": mock_context,
        })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "You can negotiate."


def test_chat_returns_404_on_unknown_session():
    with patch("app.main.gemini_chat", new=AsyncMock(side_effect=ValueError("Session 'x' not found"))):
        resp = client.post("/chat", json={
            "session_id": "unknown",
            "message": "hello",
            "context": {
                "violations": [],
                "complaints": [],
                "litigations": [],
                "risk_profile": {"score": 0, "caution_level": "Low", "reasons": []},
            },
        })

    assert resp.status_code == 404


def test_compute_risk_high_on_class_c():
    from app.main import _compute_risk
    violations = [{"class": "C"}, {"class": "C"}]
    rp = _compute_risk(violations, [])
    assert rp.caution_level == "High"
    assert rp.score >= 5


def test_compute_risk_low_on_no_violations():
    from app.main import _compute_risk
    rp = _compute_risk([], [])
    assert rp.caution_level == "Low"
    assert rp.score == 0
