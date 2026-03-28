import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.voice_bridge import VoiceBridge
from app.models.schemas import RiskProfile


@pytest.fixture
def bridge():
    with patch("app.services.voice_bridge.genai.Client"):
        return VoiceBridge()


@pytest.mark.asyncio
async def test_handle_tool_call_returns_summary_to_gemini(bridge):
    mock_live_session = AsyncMock()

    mock_fc = MagicMock()
    mock_fc.name = "lookup_building"
    mock_fc.id = "call-1"
    mock_fc.args = {
        "house_number": "123",
        "street_name": "Main Street",
        "borough": "Brooklyn",
    }

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    fake_data = {
        "violations": [{"class": "C", "novdescription": "No heat"}],
        "complaints": [],
        "litigations": [],
        "data_warning": False,
    }
    fake_risk = RiskProfile(caution_level="High", score=4, reasons=["Class C: No heat"])
    fake_summary = "This building has a High risk. No heat violation on record."

    with patch("app.services.voice_bridge.fetch_all", AsyncMock(return_value=fake_data)), \
         patch("app.services.voice_bridge.compute_risk", return_value=fake_risk), \
         patch("app.services.voice_bridge.generate_voice_analysis", AsyncMock(return_value=fake_summary)):

        await bridge._handle_tool_call(mock_tool_call, mock_live_session)

    mock_live_session.send.assert_called_once()
    call_args = mock_live_session.send.call_args
    responses = call_args.kwargs["input"].function_responses
    assert len(responses) == 1
    result = responses[0].response
    assert "summary" in result
    assert result["summary"] == fake_summary
    assert result["risk_level"] == "High"
    assert "data_warning" in result


@pytest.mark.asyncio
async def test_handle_tool_call_timeout_returns_data_warning(bridge):
    import asyncio
    mock_live_session = AsyncMock()

    mock_fc = MagicMock()
    mock_fc.name = "lookup_building"
    mock_fc.id = "call-2"
    mock_fc.args = {
        "house_number": "456",
        "street_name": "Broadway",
        "borough": "Manhattan",
    }

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    async def slow_fetch(*args, **kwargs):
        await asyncio.sleep(999)

    fake_risk = RiskProfile(caution_level="Low", score=0, reasons=[])
    fake_summary = "Sorry, data unavailable."

    with patch("app.services.voice_bridge.fetch_all", slow_fetch), \
         patch("app.services.voice_bridge.compute_risk", return_value=fake_risk), \
         patch("app.services.voice_bridge.generate_voice_analysis", AsyncMock(return_value=fake_summary)):

        await bridge._handle_tool_call(mock_tool_call, mock_live_session)

    call_args = mock_live_session.send.call_args
    result = call_args.kwargs["input"].function_responses[0].response
    assert result["data_warning"] is True
