import asyncio
import audioop
import base64
import json
from pathlib import Path

import google.genai as genai
from fastapi import WebSocket
from google.genai import types

from app.core.config import settings
from app.services.nyc_service import fetch_all
from app.services.risk_service import compute_risk

_PROMPT_PATH = Path(__file__).parent.parent / "templates" / "voice_advocate_prompt.txt"
_VOICE_PROMPT = _PROMPT_PATH.read_text()

_LOOKUP_BUILDING_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="lookup_building",
            description=(
                "Look up NYC building violation, complaint, and litigation records "
                "for a given address. Call this whenever the caller provides an address "
                "or mentions a different address."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "house_number": types.Schema(
                        type=types.Type.STRING,
                        description="Building house number, e.g. '123'",
                    ),
                    "street_name": types.Schema(
                        type=types.Type.STRING,
                        description="Street name, e.g. 'Main Street'",
                    ),
                    "borough": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "NYC borough — one of: Manhattan, Bronx, Brooklyn, "
                            "Queens, Staten Island"
                        ),
                    ),
                },
                required=["house_number", "street_name", "borough"],
            ),
        )
    ]
)

_LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=types.Content(
        parts=[types.Part(text=_VOICE_PROMPT)]
    ),
    tools=[_LOOKUP_BUILDING_TOOL],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    ),
)


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


class VoiceBridge:
    def __init__(self) -> None:
        # Gemini Live requires Developer API (not Vertex AI); vertexai=False
        # overrides the GOOGLE_GENAI_USE_VERTEXAI=1 env var set by config.py
        self._client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            vertexai=False,
            http_options=types.HttpOptions(api_version="v1alpha"),
        )
        self._stream_sid: str | None = None
        self._ratecv_state = None

    async def run(self, websocket: WebSocket) -> None:
        """Open Gemini Live session and bridge audio bidirectionally with Twilio."""
        async with self._client.aio.live.connect(
            model=settings.GEMINI_LIVE_MODEL_NAME,
            config=_LIVE_CONFIG,
        ) as live_session:
            await asyncio.gather(
                self._twilio_to_gemini(websocket, live_session),
                self._gemini_to_twilio(websocket, live_session),
            )

    async def _twilio_to_gemini(self, websocket: WebSocket, live_session) -> None:
        """Forward audio from Twilio WebSocket to Gemini Live."""
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")
            if event == "start":
                self._stream_sid = msg["start"]["streamSid"]
            elif event == "media":
                mulaw = base64.b64decode(msg["media"]["payload"])
                pcm16 = _mulaw_to_pcm16(mulaw)
                await live_session.send(
                    input={"data": pcm16, "mime_type": "audio/pcm;rate=16000"},
                    end_of_turn=False,
                )
            elif event == "stop":
                break

    async def _gemini_to_twilio(self, websocket: WebSocket, live_session) -> None:
        """Forward audio from Gemini Live back to Twilio, dispatch tool calls."""
        async for response in live_session.receive():
            if response.tool_call:
                await self._handle_tool_call(response.tool_call, live_session)
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        mulaw, self._ratecv_state = _pcm16_to_mulaw(
                            part.inline_data.data, self._ratecv_state
                        )
                        if self._stream_sid:
                            await websocket.send_text(json.dumps({
                                "event": "media",
                                "streamSid": self._stream_sid,
                                "media": {
                                    "payload": base64.b64encode(mulaw).decode()
                                },
                            }))

    async def _handle_tool_call(self, tool_call, live_session) -> None:
        """Execute lookup_building and return results to Gemini Live."""
        responses = []
        for fc in tool_call.function_calls:
            if fc.name == "lookup_building":
                args = dict(fc.args)
                data = await fetch_all(
                    house_number=args["house_number"],
                    street_name=args["street_name"],
                    borough=args["borough"],
                )
                risk = compute_risk(data["violations"], data["litigations"])
                result = {
                    "risk_level": risk.caution_level,
                    "risk_score": risk.score,
                    "risk_reasons": risk.reasons,
                    "violations_count": len(data["violations"]),
                    "complaints_count": len(data["complaints"]),
                    "litigations_count": len(data["litigations"]),
                    "violations_sample": data["violations"][:5],
                    "litigations_sample": data["litigations"][:3],
                    "data_warning": data["data_warning"],
                }
                responses.append(
                    types.FunctionResponse(
                        name=fc.name,
                        id=fc.id,
                        response=result,
                    )
                )
        if responses:
            await live_session.send(
                input=types.LiveClientToolResponse(function_responses=responses)
            )
