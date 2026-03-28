import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.voice_bridge import _mulaw_to_pcm16, _pcm16_to_mulaw


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
