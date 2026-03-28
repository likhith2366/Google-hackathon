import base64
import hashlib
import hmac
import logging

import google.genai as genai
from fastapi import APIRouter, HTTPException, Request, WebSocket
from fastapi.responses import Response
from google.genai import types

logger = logging.getLogger(__name__)

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


@router.get("/debug-models")
async def debug_models():
    """List models available to the configured API key (for debugging)."""
    client = genai.Client(
        api_key=settings.GOOGLE_API_KEY,
        vertexai=False,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    models = [m.name async for m in await client.aio.models.list()]
    live_models = [m for m in models if "live" in m.lower() or "flash" in m.lower()]
    return {"all_count": len(models), "live_or_flash": live_models}


@router.post("/incoming")
async def incoming_call(request: Request):
    """TwiML webhook — Twilio calls this when a call arrives."""
    if settings.TWILIO_AUTH_TOKEN:
        signature = request.headers.get("X-Twilio-Signature", "")
        # Cloud Run sits behind a TLS-terminating proxy — reconstruct the public HTTPS URL
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("host", request.url.netloc)
        url = f"{proto}://{host}{request.url.path}"
        form = dict(await request.form())
        if not _validate_twilio_signature(
            settings.TWILIO_AUTH_TOKEN, url, form, signature
        ):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    host = request.headers.get("host", request.url.netloc)
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    ws_scheme = "wss" if proto == "https" else "ws"
    stream_url = f"{ws_scheme}://{host}/voice/stream"

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
    except Exception as exc:
        logger.exception("VoiceBridge error: %s", exc)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
