import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.schemas import ParsedAddress, RiskProfile
from app.services.gemini_service import extract_address, generate_summary, chat


async def test_extract_address_returns_parsed_address():
    mock_response = MagicMock()
    mock_response.text = '{"house_number": "123", "street_name": "Main St", "borough": "Brooklyn"}'

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await extract_address("123 Main St Brooklyn")

    assert isinstance(result, ParsedAddress)
    assert result.house_number == "123"
    assert result.street_name == "Main St"
    assert result.borough == "Brooklyn"


async def test_extract_address_returns_none_on_bad_json():
    mock_response = MagicMock()
    mock_response.text = "I cannot parse that."

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await extract_address("not an address")

    assert result is None


async def test_generate_summary_returns_text_and_session_id():
    addr = ParsedAddress(house_number="1", street_name="Broadway", borough="Manhattan")
    rp = RiskProfile(score=4, caution_level="Moderate", reasons=["2 Class B violations"])

    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True
    mock_event.content.parts = [MagicMock(text="Your building has issues.")]

    async def mock_run_async(**kwargs):
        yield mock_event

    with patch("app.services.gemini_service._runner") as mock_runner, \
         patch("app.services.gemini_service.session_service") as mock_ss:
        mock_runner.run_async = mock_run_async
        mock_session = MagicMock()
        mock_session.id = "adk-session-abc"
        mock_ss.create_session = AsyncMock(return_value=mock_session)

        summary, session_id = await generate_summary(
            address=addr,
            violations=[],
            complaints=[],
            litigations=[],
            risk_profile=rp,
        )

    assert "issues" in summary
    assert session_id is not None


async def test_chat_raises_on_unknown_session():
    from app.services.gemini_service import chat
    with pytest.raises(ValueError, match="Session .* not found"):
        await chat("nonexistent-session-id", "any message")
