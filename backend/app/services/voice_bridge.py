import audioop


def _mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """Convert Twilio mulaw 8kHz → PCM16 16kHz for Gemini Live."""
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k


def _pcm16_to_mulaw(pcm_bytes: bytes, state=None) -> tuple[bytes, object]:
    """Convert Gemini Live PCM16 24kHz → mulaw 8kHz for Twilio."""
    pcm_8k, new_state = audioop.ratecv(pcm_bytes, 2, 1, 24000, 8000, state)
    mulaw = audioop.lin2ulaw(pcm_8k, 2)
    return mulaw, new_state
