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
