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
