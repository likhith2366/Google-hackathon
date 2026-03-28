import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.voice_bridge import VoiceBridge, _mulaw_to_pcm16, _pcm16_to_mulaw


# --- Audio conversion ---

def test_mulaw_to_pcm16_returns_bytes():
    mulaw_silence = bytes([0x7F] * 160)
    result = _mulaw_to_pcm16(mulaw_silence)
    assert isinstance(result, bytes)


def test_mulaw_to_pcm16_doubles_sample_count():
    # 160 mulaw samples at 8kHz → ~320 samples at 16kHz → ~640 bytes (2 bytes/sample)
    # audioop.ratecv may vary by a frame, so allow ±4 bytes
    mulaw = bytes([0x7F] * 160)
    pcm16 = _mulaw_to_pcm16(mulaw)
    assert 636 <= len(pcm16) <= 644


def test_pcm16_to_mulaw_returns_tuple():
    pcm = bytes(960)  # 480 samples * 2 bytes at 24kHz
    mulaw, state = _pcm16_to_mulaw(pcm, None)
    assert isinstance(mulaw, bytes)
    assert state is not None


def test_pcm16_to_mulaw_reduces_sample_count():
    # 480 samples at 24kHz → 160 samples at 8kHz → 160 bytes (1 byte/sample in mulaw)
    pcm = bytes(960)  # 480 samples * 2 bytes
    mulaw, _ = _pcm16_to_mulaw(pcm, None)
    assert len(mulaw) == 160


# --- Tool dispatch ---

@pytest.mark.asyncio
async def test_handle_tool_call_lookup_building_returns_risk():
    bridge = VoiceBridge.__new__(VoiceBridge)
    bridge._stream_sid = "MX123"
    bridge._ratecv_state = None

    mock_fc = MagicMock()
    mock_fc.name = "lookup_building"
    mock_fc.id = "call-1"
    mock_fc.args = {
        "house_number": "123",
        "street_name": "Main St",
        "borough": "Brooklyn",
    }

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    mock_live_session = AsyncMock()

    mock_data = {
        "violations": [{"class": "C"}],
        "complaints": [],
        "litigations": [],
        "data_warning": False,
    }

    with patch("app.services.voice_bridge.fetch_all", new=AsyncMock(return_value=mock_data)):
        await bridge._handle_tool_call(mock_tool_call, mock_live_session)

    mock_live_session.send.assert_called_once()
    sent_input = mock_live_session.send.call_args.kwargs["input"]
    assert len(sent_input.function_responses) == 1
    assert sent_input.function_responses[0].name == "lookup_building"
    result = sent_input.function_responses[0].response
    assert result["risk_level"] == "Moderate"  # 1x Class C = score 4, threshold High=5
    assert result["violations_count"] == 1


@pytest.mark.asyncio
async def test_handle_tool_call_data_warning_propagated():
    bridge = VoiceBridge.__new__(VoiceBridge)
    bridge._stream_sid = "MX123"
    bridge._ratecv_state = None

    mock_fc = MagicMock()
    mock_fc.name = "lookup_building"
    mock_fc.id = "call-2"
    mock_fc.args = {
        "house_number": "999",
        "street_name": "Fake St",
        "borough": "Manhattan",
    }

    mock_tool_call = MagicMock()
    mock_tool_call.function_calls = [mock_fc]

    mock_live_session = AsyncMock()

    mock_data = {
        "violations": [],
        "complaints": [],
        "litigations": [],
        "data_warning": True,
    }

    with patch("app.services.voice_bridge.fetch_all", new=AsyncMock(return_value=mock_data)):
        await bridge._handle_tool_call(mock_tool_call, mock_live_session)

    sent_input = mock_live_session.send.call_args.kwargs["input"]
    assert sent_input.function_responses[0].response["data_warning"] is True
