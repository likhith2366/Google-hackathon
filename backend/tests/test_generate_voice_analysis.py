import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.gemini_service import generate_voice_analysis
from app.models.schemas import ParsedAddress, RiskProfile


@pytest.fixture
def sample_data():
    address = ParsedAddress(house_number="123", street_name="Main Street", borough="Brooklyn")
    violations = [{"class": "C", "novdescription": "No heat"}]
    complaints = []
    litigations = []
    risk = RiskProfile(caution_level="High", score=4, reasons=["Class C violation: No heat"])
    return address, violations, complaints, litigations, risk


@pytest.mark.asyncio
async def test_generate_voice_analysis_returns_string(sample_data):
    address, violations, complaints, litigations, risk = sample_data

    mock_response = MagicMock()
    mock_response.text = "This building has a High risk level due to no heat violations."

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await generate_voice_analysis(address, violations, complaints, litigations, risk)

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_generate_voice_analysis_includes_address(sample_data):
    address, violations, complaints, litigations, risk = sample_data

    mock_response = MagicMock()
    mock_response.text = "123 Main Street Brooklyn: High risk. No heat violation."

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await generate_voice_analysis(address, violations, complaints, litigations, risk)

    assert "123" in result or "Main Street" in result or "Brooklyn" in result


@pytest.mark.asyncio
async def test_generate_voice_analysis_handles_none_response(sample_data):
    address, violations, complaints, litigations, risk = sample_data
    mock_response = MagicMock()
    mock_response.text = None

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await generate_voice_analysis(address, violations, complaints, litigations, risk)

    assert isinstance(result, str)
    assert len(result) > 0
