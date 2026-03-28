# Voice Interface Design — Gemini Live API + Twilio

**Date:** 2026-03-28
**Status:** Approved

## Overview

Add a phone-call voice interface to BeforeYouSign as a second interface alongside the existing web frontend. Callers dial a Twilio number, speak an address, and receive a live AI-powered tenant advocacy response using the same NYC Open Data logic and Gemini advocate persona as the web app.

The AI layer is fully GCP-native: Gemini Live API (`gemini-2.0-flash-live-001`) handles real-time speech-to-text, reasoning, and text-to-speech in a single streaming session. Twilio provides PSTN (phone number + audio transport) — GCP has no equivalent service.

## Architecture

```
Caller
  │ dials Twilio number
  ▼
Twilio (PSTN)
  │ POST /voice/incoming  ← TwiML webhook
  ▼
FastAPI (Cloud Run)
  │ returns TwiML: <Connect><Stream url="wss://.../voice/stream"/>
  ▼
Twilio Media Streams
  │ WebSocket: mulaw 8kHz audio chunks (bidirectional)
  ▼
VoiceBridge (WebSocket handler on Cloud Run)
  │ audio conversion: mulaw 8kHz ↔ PCM16 16kHz
  ├─ calls nyc_service.fetch_all() when Gemini invokes lookup_building tool
  └─ loads advocate_prompt.txt as system instruction
  ▼
Gemini Live API  (gemini-2.0-flash-live-001)
  └─ function tool: lookup_building(address) → violations + risk profile
```

## Call Flow

1. Caller dials Twilio number → Twilio POSTs to `POST /voice/incoming`
2. FastAPI returns TwiML `<Connect><Stream>` pointing to `wss://{host}/voice/stream`
3. Twilio opens WebSocket to `/voice/stream`
4. Bridge opens a Gemini Live session with `advocate_prompt.txt` as system instruction and `lookup_building` registered as a function tool
5. Gemini greets the caller and asks for their address
6. Caller speaks address → Gemini transcribes and invokes `lookup_building(address)`
7. Bridge executes `nyc_service.fetch_all()` + `_compute_risk()` and returns JSON to Gemini
8. Gemini speaks back a summary using the advocate persona
9. Multi-turn Q&A continues for the rest of the call
10. If the caller mentions a different address at any point, Gemini re-invokes `lookup_building` with the new address; bridge fetches fresh data

## Components

### New Files

**`backend/app/routers/voice.py`**
- `POST /voice/incoming` — validates `X-Twilio-Signature`, returns TwiML `<Connect><Stream>`
- `WebSocket /voice/stream` — accepts Twilio connection, instantiates `VoiceBridge`, runs send/receive loops with `asyncio.gather`

**`backend/app/services/voice_bridge.py`**
- On connect: open Gemini Live session with system instruction + `lookup_building` tool definition
- Audio in: base64-decode mulaw from Twilio → `audioop.ulaw2lin` → `audioop.ratecv` to 16kHz → send PCM16 to Gemini Live
- Audio out: receive PCM16 24kHz from Gemini → `audioop.ratecv` to 8kHz → `audioop.lin2ulaw` → base64 → send to Twilio
- Tool dispatch: on `lookup_building(address)` call → `gemini_service.extract_address()` → `nyc_service.fetch_all()` → `_compute_risk()` → return result JSON to Gemini Live session

### Modified Files

**`backend/app/main.py`** — add `app.include_router(voice_router)`; extract `_compute_risk()` to `backend/app/services/risk_service.py` so both `main.py` and `voice_bridge.py` can import it without circular dependency

**`backend/app/core/config.py`** — add `GEMINI_LIVE_MODEL_NAME: str = "gemini-2.0-flash-live-001"`

**`backend/app/templates/advocate_prompt.txt`** — add voice-specific addendum: instruct Gemini to re-call `lookup_building` if the caller mentions a new address, and to treat the most recent tool result as the active building context

**`backend/requirements.txt`** — add `audioop-lts` (Python 3.11+ stdlib shim for audio conversion)

## Configuration

| Variable | Description |
|---|---|
| `GEMINI_LIVE_MODEL_NAME` | `gemini-2.0-flash-live-001` |
| `TWILIO_AUTH_TOKEN` | Used to validate `X-Twilio-Signature` on incoming webhooks |

Twilio webhook URL is set in the Twilio console to `https://{cloud-run-url}/voice/incoming`. No other Twilio credentials are stored in the backend.

**Cloud Run:** Raise request timeout to **3600s** (max) — calls are long-lived WebSocket connections that exceed the default 60s timeout.

## Error Handling

| Scenario | Handling |
|---|---|
| Gemini Live session fails to open | Return TwiML `<Say>` error message + `<Hangup>` instead of `<Stream>` |
| Socrata API down / address not found | Return `data_warning` in tool result; advocate prompt already handles gracefully |
| Address cannot be parsed | Gemini asks caller to repeat/clarify |
| Caller changes address mid-call | `lookup_building` re-invoked with new address; most recent result becomes active context |
| Caller interrupts Gemini mid-speech | Gemini Live barge-in handled natively |
| Spoofed webhook | `X-Twilio-Signature` validated on `POST /voice/incoming` |
| Long call timeout | Cloud Run timeout set to 3600s |

## What Is Not Changing

- Existing `/analyze` and `/chat` endpoints — untouched
- `nyc_service.py`, `gemini_service.py`, risk scoring logic — reused as-is
- Frontend — no changes
- ADK session management for web — unchanged; voice uses Gemini Live sessions separately
