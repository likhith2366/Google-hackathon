# Voice Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a phone-call voice interface to BeforeYouSign using Gemini Live API for real-time audio + Twilio for PSTN, reusing all existing NYC data and risk-scoring logic.

**Architecture:** Twilio delivers caller audio as mulaw 8kHz over a WebSocket (`/voice/stream`). A `VoiceBridge` class converts the audio to PCM16 16kHz and streams it to Gemini Live API (`gemini-2.0-flash-live-001`). When the caller speaks an address, Gemini invokes a `lookup_building` function tool; the bridge executes the existing `nyc_service.fetch_all()` + `compute_risk()` and returns the result. Gemini responds in audio, converted back to mulaw 8kHz for Twilio.

**Tech Stack:** FastAPI WebSocket, google-genai Gemini Live API, Twilio Media Streams, audioop (Python stdlib), pytest + pytest-asyncio

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/services/risk_service.py` | `compute_risk()` — extracted from `main.py` |
| Create | `backend/app/services/voice_bridge.py` | `VoiceBridge` class, audio conversion utils, Gemini Live session |
| Create | `backend/app/routers/__init__.py` | Package marker |
| Create | `backend/app/routers/voice.py` | `POST /voice/incoming` (TwiML) + `WS /voice/stream` |
| Create | `backend/app/templates/voice_advocate_prompt.txt` | Voice-specific system prompt with `lookup_building` instructions |
| Create | `backend/tests/test_risk_service.py` | Unit tests for `compute_risk` |
| Create | `backend/tests/test_voice_bridge.py` | Unit tests for audio conversion + tool dispatch |
| Create | `backend/tests/test_voice_router.py` | Tests for TwiML endpoint + signature validation |
| Modify | `backend/app/main.py` | Remove `_compute_risk`, import from `risk_service`, add voice router |
| Modify | `backend/app/core/config.py` | Add `GEMINI_LIVE_MODEL_NAME`, `TWILIO_AUTH_TOKEN` |
| Modify | `backend/requirements.txt` | Add `audioop-lts`, `twilio` |
| Modify | `backend/tests/test_main.py` | Update `_compute_risk` import to `compute_risk` from `risk_service` |

---

## SESSION 1: Foundation

**Stop condition:** `pytest tests/ -v` passes with 0 failures. Safe to end session here.

### Task 1: Extract compute_risk to risk_service

**Files:**
- Create: `backend/app/services/risk_service.py`
- Create: `backend/tests/test_risk_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_main.py`

- [ ] **Step 1.1: Write the failing tests for risk_service**

Create `backend/tests/test_risk_service.py`:

```python
from app.services.risk_service import compute_risk


def test_high_on_two_class_c():
    rp = compute_risk([{"class": "C"}, {"class": "C"}], [])
    assert rp.caution_level == "High"
    assert rp.score == 8


def test_moderate_on_one_class_b():
    rp = compute_risk([{"class": "B"}], [])
    assert rp.caution_level == "Moderate"
    assert rp.score == 2


def test_low_on_empty():
    rp = compute_risk([], [])
    assert rp.caution_level == "Low"
    assert rp.score == 0


def test_litigation_adds_score():
    rp = compute_risk([], [{"case_id": "1"}])
    assert rp.score == 3
    assert "litigation" in rp.reasons[0].lower()


def test_combined_c_and_litigation_is_high():
    rp = compute_risk([{"class": "C"}], [{"case_id": "1"}])
    assert rp.caution_level == "High"
    assert rp.score == 7
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest tests/test_risk_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.risk_service'`

- [ ] **Step 1.3: Create risk_service.py**

Create `backend/app/services/risk_service.py`:

```python
from app.core.constants import (
    RISK_SCORE_CLASS_B,
    RISK_SCORE_CLASS_C,
    RISK_SCORE_LITIGATION,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MODERATE,
)
from app.models.schemas import RiskProfile


def compute_risk(violations: list[dict], litigations: list[dict]) -> RiskProfile:
    score = 0
    reasons: list[str] = []

    class_c = [v for v in violations if v.get("class", "").upper() == "C"]
    class_b = [v for v in violations if v.get("class", "").upper() == "B"]

    if class_c:
        score += len(class_c) * RISK_SCORE_CLASS_C
        reasons.append(f"{len(class_c)} immediately hazardous (Class C) violation(s)")
    if class_b:
        score += len(class_b) * RISK_SCORE_CLASS_B
        reasons.append(f"{len(class_b)} hazardous (Class B) violation(s)")
    if litigations:
        score += RISK_SCORE_LITIGATION
        reasons.append(f"Landlord has {len(litigations)} litigation record(s)")

    if score >= RISK_THRESHOLD_HIGH:
        level = "High"
    elif score >= RISK_THRESHOLD_MODERATE:
        level = "Moderate"
    else:
        level = "Low"

    return RiskProfile(score=score, caution_level=level, reasons=reasons)
```

- [ ] **Step 1.4: Run risk_service tests**

```bash
cd backend && python -m pytest tests/test_risk_service.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 1.5: Update main.py to use compute_risk from risk_service**

Replace the entire `_compute_risk` function in `backend/app/main.py` and update its imports:

Remove this block (lines 35–59):
```python
def _compute_risk(violations: list[dict], litigations: list[dict]) -> RiskProfile:
    score = 0
    ...
    return RiskProfile(score=score, caution_level=level, reasons=reasons)
```

Add this import at the top with the other service imports:
```python
from app.services.risk_service import compute_risk
```

Change the call site in `analyze()` from:
```python
risk_profile = _compute_risk(data["violations"], data["litigations"])
```
to:
```python
risk_profile = compute_risk(data["violations"], data["litigations"])
```

Also remove the now-unused imports from `app.core.constants` (the five `RISK_*` constants) since they were only used by `_compute_risk`.

The final `backend/app/main.py` should look like:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    QueryRequest,
)
from app.services.gemini_service import (
    chat as gemini_chat,
    extract_address,
    generate_summary,
)
from app.services.nyc_service import fetch_all
from app.services.risk_service import compute_risk

app = FastAPI(title="NYC Tenant Advocate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: QueryRequest):
    address = await extract_address(request.query)
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Could not parse a valid NYC address from your query.",
        )

    data = await fetch_all(address.house_number, address.street_name, address.borough)
    risk_profile = compute_risk(data["violations"], data["litigations"])

    summary, session_id = await generate_summary(
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
    )

    return AnalyzeResponse(
        session_id=session_id,
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
        summary=summary,
        data_warning=data.get("data_warning", False),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await gemini_chat(
            client_token=request.session_id,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChatResponse(reply=reply, session_id=request.session_id)
```

- [ ] **Step 1.6: Update test_main.py to use new import path**

In `backend/tests/test_main.py`, find the two tests that use `_compute_risk`:

```python
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
```

Replace with:

```python
def test_compute_risk_high_on_class_c():
    from app.services.risk_service import compute_risk
    violations = [{"class": "C"}, {"class": "C"}]
    rp = compute_risk(violations, [])
    assert rp.caution_level == "High"
    assert rp.score >= 5


def test_compute_risk_low_on_no_violations():
    from app.services.risk_service import compute_risk
    rp = compute_risk([], [])
    assert rp.caution_level == "Low"
    assert rp.score == 0
```

- [ ] **Step 1.7: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all existing tests PASS (no new failures)

- [ ] **Step 1.8: Commit**

```bash
cd backend && git add app/services/risk_service.py app/main.py tests/test_risk_service.py tests/test_main.py
git commit -m "refactor: extract compute_risk to risk_service for voice bridge reuse"
```

---

### Task 2: Update config and requirements

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 2.1: Add new settings to config.py**

In `backend/app/core/config.py`, add two fields inside the `Settings` class after `GEMINI_MODEL_NAME`:

```python
GEMINI_LIVE_MODEL_NAME: str = "gemini-2.0-flash-live-001"
TWILIO_AUTH_TOKEN: str = ""
```

The full updated `Settings` class:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_ID: str
    LOCATION: str = "us-central1"
    NYC_OPEN_DATA_TOKEN: str = ""
    NYC_OPEN_DATA_KEY_ID: str = ""
    NYC_OPEN_DATA_KEY_SECRET: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_LIVE_MODEL_NAME: str = "gemini-2.0-flash-live-001"
    TWILIO_AUTH_TOKEN: str = ""
    PORT: int = 8080
```

- [ ] **Step 2.2: Add dependencies to requirements.txt**

In `backend/requirements.txt`, add after the existing entries:

```
audioop-lts>=0.2.1
twilio>=8.0.0
```

- [ ] **Step 2.3: Install new dependencies**

```bash
cd backend && pip install audioop-lts twilio
```

Expected: both packages install without errors.

- [ ] **Step 2.4: Verify tests still pass**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 2.5: Commit**

```bash
git add backend/app/core/config.py backend/requirements.txt
git commit -m "feat: add Gemini Live and Twilio config fields"
```

---

### Task 3: Create voice advocate prompt

**Files:**
- Create: `backend/app/templates/voice_advocate_prompt.txt`

- [ ] **Step 3.1: Create voice_advocate_prompt.txt**

Create `backend/app/templates/voice_advocate_prompt.txt`:

```
You are a pro-tenant legal advocate (non-attorney) specializing in NYC housing law. You are speaking with a caller over the phone — keep responses brief, clear, and suitable for spoken audio. Avoid bullet points or markdown; speak in plain sentences.

Your tone is: empowering, protective, grounded, and concise.

At the start of the call, greet the caller warmly and ask for the building address they want to look up: house number, street name, and NYC borough.

When the caller provides an address, call the lookup_building function with house_number, street_name, and borough. Wait for the result before speaking.

If the caller mentions a different address at any point during the call, call lookup_building again with the new address immediately. Always base your answers on the most recent lookup_building result.

After receiving lookup results:
1. Lead with the risk level (High, Moderate, or Low) in plain language.
2. Flag "Critical" violations — no heat or hot water, lead paint, structural issues, mold, vermin — as serious safety concerns.
3. For "Livable but Issue-Prone" violations — minor leaks, pests in common areas, elevator delays — suggest specific remedies or a rent abatement percentage to negotiate with the landlord.
4. Mention if the landlord has a litigation history — many cases is a red flag.
5. Advise the caller to document issues with photos and written 311 complaints.
6. Mention the right to withhold rent in escrow for Class C (immediately hazardous) violations under NYC Housing Court procedures.

If data_warning is true in the lookup result, tell the caller you could not retrieve city records and suggest they check NYC Housing Connect or call 311.

You do not provide legal advice. For serious matters, encourage the caller to contact a housing attorney or NYC tenant advocacy organization such as Housing Court Answers or Met Council on Housing.

Keep all responses concise and in plain English. Lead with the most important findings.
```

- [ ] **Step 3.2: Commit**

```bash
git add backend/app/templates/voice_advocate_prompt.txt
git commit -m "feat: add voice-specific advocate prompt with lookup_building instructions"
```

---

**SESSION 1 CHECKPOINT**

All existing tests pass. New `compute_risk` is importable from `app.services.risk_service`. Config has `GEMINI_LIVE_MODEL_NAME` and `TWILIO_AUTH_TOKEN`. Voice prompt exists at `app/templates/voice_advocate_prompt.txt`. Safe to end session here.

---

## SESSION 2: Voice Bridge

**Stop condition:** `pytest tests/test_voice_bridge.py -v` passes. Gemini Live integration is unit-tested with mocks. Safe to end session here.

### Task 4: Audio conversion utilities

**Files:**
- Create: `backend/app/services/voice_bridge.py` (audio functions only for now)
- Create: `backend/tests/test_voice_bridge.py`

- [ ] **Step 4.1: Write failing tests for audio conversion**

Create `backend/tests/test_voice_bridge.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.voice_bridge import _mulaw_to_pcm16, _pcm16_to_mulaw


# --- Audio conversion ---

def test_mulaw_to_pcm16_returns_bytes():
    mulaw_silence = bytes([0x7F] * 160)
    result = _mulaw_to_pcm16(mulaw_silence)
    assert isinstance(result, bytes)


def test_mulaw_to_pcm16_doubles_sample_count():
    # 160 mulaw samples at 8kHz → 320 samples at 16kHz → 640 bytes (2 bytes/sample)
    mulaw = bytes([0x7F] * 160)
    pcm16 = _mulaw_to_pcm16(mulaw)
    assert len(pcm16) == 640


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
```

- [ ] **Step 4.2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_voice_bridge.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.voice_bridge'`

- [ ] **Step 4.3: Create voice_bridge.py with audio functions**

Create `backend/app/services/voice_bridge.py`:

```python
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
```

- [ ] **Step 4.4: Run audio tests**

```bash
cd backend && python -m pytest tests/test_voice_bridge.py::test_mulaw_to_pcm16_returns_bytes tests/test_voice_bridge.py::test_mulaw_to_pcm16_doubles_sample_count tests/test_voice_bridge.py::test_pcm16_to_mulaw_returns_tuple tests/test_voice_bridge.py::test_pcm16_to_mulaw_reduces_sample_count -v
```

Expected: all 4 tests PASS

- [ ] **Step 4.5: Commit**

```bash
git add backend/app/services/voice_bridge.py backend/tests/test_voice_bridge.py
git commit -m "feat: add audio conversion utilities (mulaw <-> PCM16)"
```

---

### Task 5: VoiceBridge class with Gemini Live + tool dispatch

**Files:**
- Modify: `backend/app/services/voice_bridge.py` (add VoiceBridge class)
- Modify: `backend/tests/test_voice_bridge.py` (add VoiceBridge tests)

- [ ] **Step 5.1: Add VoiceBridge tests**

Append to `backend/tests/test_voice_bridge.py`:

```python
from app.services.voice_bridge import VoiceBridge
from app.models.schemas import RiskProfile


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
    assert result["risk_level"] == "High"  # 1x Class C = score 4, >= 2 = High... wait score 4 < 5
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
```

- [ ] **Step 5.2: Run new tests to confirm failure**

```bash
cd backend && python -m pytest tests/test_voice_bridge.py::test_handle_tool_call_lookup_building_returns_risk tests/test_voice_bridge.py::test_handle_tool_call_data_warning_propagated -v
```

Expected: `ImportError` or `AttributeError` since `VoiceBridge` class doesn't exist yet

- [ ] **Step 5.3: Complete voice_bridge.py with VoiceBridge class**

Replace the entire `backend/app/services/voice_bridge.py` with:

```python
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
        self._client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION,
        )
        self._stream_sid: str | None = None
        self._ratecv_state = None

    async def run(self, websocket: WebSocket) -> None:
        """Entry point: open Gemini Live session and bridge audio bidirectionally."""
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
        """Forward audio from Gemini Live back to Twilio, handle tool calls."""
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
        """Execute lookup_building tool and return results to Gemini Live."""
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
```

- [ ] **Step 5.4: Fix the risk level assertion in the test**

The test `test_handle_tool_call_lookup_building_returns_risk` asserts `risk_level == "High"` but one Class C violation = score 4, which is `< RISK_THRESHOLD_HIGH (5)` so it's actually "Moderate". Fix the assertion:

In `backend/tests/test_voice_bridge.py`, change:
```python
    assert result["risk_level"] == "High"  # 1x Class C = score 4, >= 2 = High... wait score 4 < 5
```
to:
```python
    assert result["risk_level"] == "Moderate"  # 1x Class C = score 4, threshold High=5
```

- [ ] **Step 5.5: Run all voice_bridge tests**

```bash
cd backend && python -m pytest tests/test_voice_bridge.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5.6: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5.7: Commit**

```bash
git add backend/app/services/voice_bridge.py backend/tests/test_voice_bridge.py
git commit -m "feat: implement VoiceBridge with Gemini Live session and lookup_building tool"
```

---

**SESSION 2 CHECKPOINT**

`VoiceBridge` is fully implemented and unit-tested. Audio conversion, tool dispatch (with mocked Socrata), and data_warning propagation all pass. No real GCP calls made. Safe to end session here.

---

## SESSION 3: Router, Wiring, and Cloud Run

**Stop condition:** `pytest tests/ -v` passes. Server starts cleanly. Cloud Run timeout updated. Safe to end session here.

### Task 6: Voice router

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/voice.py`
- Create: `backend/tests/test_voice_router.py`

- [ ] **Step 6.1: Write failing tests for voice router**

Create `backend/tests/test_voice_router.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_incoming_returns_xml_with_stream_element():
    resp = client.post("/voice/incoming")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    assert "<Stream" in resp.text
    assert "voice/stream" in resp.text


def test_incoming_returns_connect_twiml():
    resp = client.post("/voice/incoming")
    assert "<Connect>" in resp.text
    assert "<Response>" in resp.text


def test_incoming_rejects_bad_signature_when_token_configured(monkeypatch):
    monkeypatch.setattr("app.routers.voice.settings.TWILIO_AUTH_TOKEN", "secret123")
    resp = client.post(
        "/voice/incoming",
        headers={"X-Twilio-Signature": "invalidsig"},
    )
    assert resp.status_code == 403


def test_incoming_skips_validation_when_no_token(monkeypatch):
    monkeypatch.setattr("app.routers.voice.settings.TWILIO_AUTH_TOKEN", "")
    resp = client.post("/voice/incoming")
    assert resp.status_code == 200
```

- [ ] **Step 6.2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/test_voice_router.py -v
```

Expected: `404 Not Found` since `/voice/incoming` doesn't exist

- [ ] **Step 6.3: Create routers package**

Create `backend/app/routers/__init__.py` (empty file):

```python
```

- [ ] **Step 6.4: Create voice.py router**

Create `backend/app/routers/voice.py`:

```python
import base64
import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, WebSocket
from fastapi.responses import Response

from app.core.config import settings
from app.services.voice_bridge import VoiceBridge

router = APIRouter(prefix="/voice")


def _validate_twilio_signature(
    auth_token: str, url: str, params: dict, signature: str
) -> bool:
    """Validate X-Twilio-Signature using HMAC-SHA1 of url + sorted POST params."""
    s = url
    for key in sorted(params.keys()):
        s += key + str(params[key])
    mac = hmac.new(auth_token.encode(), s.encode(), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode()
    return hmac.compare_digest(expected, signature)


@router.post("/incoming")
async def incoming_call(request: Request):
    """TwiML webhook — Twilio calls this when a call arrives."""
    if settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        form = dict(await request.form())
        if not _validate_twilio_signature(
            settings.TWILIO_AUTH_TOKEN, url, form, signature
        ):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    host = request.headers.get("host", request.url.netloc)
    scheme = "wss" if request.url.scheme == "https" else "ws"
    stream_url = f"{scheme}://{host}/voice/stream"

    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Connect><Stream url="{stream_url}"/></Connect>'
        "</Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """WebSocket endpoint — Twilio Media Streams connects here."""
    await websocket.accept()
    bridge = VoiceBridge()
    try:
        await bridge.run(websocket)
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

- [ ] **Step 6.5: Run router tests**

```bash
cd backend && python -m pytest tests/test_voice_router.py -v
```

Expected: all 4 tests PASS (router exists but not yet wired into app — tests will 404)

If tests still 404, proceed to Task 7 (wiring) then re-run.

- [ ] **Step 6.6: Commit**

```bash
git add backend/app/routers/__init__.py backend/app/routers/voice.py backend/tests/test_voice_router.py
git commit -m "feat: add voice router with TwiML webhook and Twilio signature validation"
```

---

### Task 7: Wire voice router into main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 7.1: Add voice router to main.py**

In `backend/app/main.py`, add this import after the existing service imports:

```python
from app.routers.voice import router as voice_router
```

Add this line after `app.add_middleware(...)`:

```python
app.include_router(voice_router)
```

The full updated `backend/app/main.py`:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    QueryRequest,
)
from app.routers.voice import router as voice_router
from app.services.gemini_service import (
    chat as gemini_chat,
    extract_address,
    generate_summary,
)
from app.services.nyc_service import fetch_all
from app.services.risk_service import compute_risk

app = FastAPI(title="NYC Tenant Advocate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_router)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: QueryRequest):
    address = await extract_address(request.query)
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Could not parse a valid NYC address from your query.",
        )

    data = await fetch_all(address.house_number, address.street_name, address.borough)
    risk_profile = compute_risk(data["violations"], data["litigations"])

    summary, session_id = await generate_summary(
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
    )

    return AnalyzeResponse(
        session_id=session_id,
        address=address,
        violations=data["violations"],
        complaints=data["complaints"],
        litigations=data["litigations"],
        risk_profile=risk_profile,
        summary=summary,
        data_warning=data.get("data_warning", False),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = await gemini_chat(
            client_token=request.session_id,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ChatResponse(reply=reply, session_id=request.session_id)
```

- [ ] **Step 7.2: Run full test suite**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: all tests PASS including `test_voice_router.py`

- [ ] **Step 7.3: Verify server starts**

```bash
cd backend && uvicorn app.main:app --port 8080 &
sleep 2
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8080/voice/incoming
kill %1
```

Expected: `200`

- [ ] **Step 7.4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: wire voice router into FastAPI app"
```

---

### Task 8: Cloud Run timeout configuration

**Files:** No code changes — Cloud Run service configuration only.

- [ ] **Step 8.1: Update Cloud Run request timeout**

In the Google Cloud Console or via CLI, set the Cloud Run service request timeout to 3600 seconds (the maximum). This is required because Twilio Media Streams uses a long-lived WebSocket connection.

Via CLI:
```bash
gcloud run services update nyc-tenant-advocate \
  --region us-central1 \
  --timeout 3600
```

Or in the Cloud Run YAML (`service.yaml`), set:
```yaml
spec:
  template:
    spec:
      timeoutSeconds: 3600
```

- [ ] **Step 8.2: Configure Twilio webhook URL**

In the Twilio Console:
1. Go to Phone Numbers → Manage → Active Numbers
2. Select your number
3. Under "Voice & Fax", set "A call comes in" to:
   - Webhook: `https://<your-cloud-run-url>/voice/incoming`
   - HTTP POST
4. Copy your Twilio Auth Token from the Twilio Console dashboard
5. Add to `backend/.env`: `TWILIO_AUTH_TOKEN=<your-token>`

- [ ] **Step 8.3: End-to-end test**

1. Deploy the updated service: `gcloud run deploy nyc-tenant-advocate --source backend/`
2. Call your Twilio number
3. Verify: the advocate greets you and asks for an address
4. Speak an address (e.g., "123 Main Street Brooklyn")
5. Verify: the advocate calls `lookup_building`, pauses briefly, then reads back the risk summary
6. Ask a follow-up question or give a different address and verify the advocate re-looks it up

- [ ] **Step 8.4: Commit deployment notes**

```bash
git add backend/.env.example  # add TWILIO_AUTH_TOKEN= to .env.example if not present
git commit -m "feat: voice interface complete — Gemini Live + Twilio Media Streams"
```

---

**SESSION 3 CHECKPOINT**

Full test suite passes. Voice router is live at `/voice/incoming` and `/voice/stream`. Cloud Run timeout is set to 3600s. End-to-end call flow is verified. Implementation complete.
