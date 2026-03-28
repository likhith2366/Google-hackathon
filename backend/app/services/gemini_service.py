import json
import uuid
from pathlib import Path

import google.genai as genai
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.core.config import settings  # sets Vertex AI env vars on import
from app.models.schemas import ParsedAddress, RiskProfile

# ── Shared services ──────────────────────────────────────────────────────────

session_service = InMemorySessionService()

_PROMPT_PATH = Path(__file__).parent.parent / "templates" / "advocate_prompt.txt"
_ADVOCATE_PROMPT = _PROMPT_PATH.read_text()

_agent = Agent(
    name="tenant_advocate",
    model=settings.GEMINI_MODEL_NAME,
    instruction=_ADVOCATE_PROMPT,
)

_runner = Runner(
    agent=_agent,
    app_name="nyc_tenant_advocate",
    session_service=session_service,
)

_genai_client = genai.Client(
    vertexai=True,
    project=settings.PROJECT_ID,
    location=settings.LOCATION,
)

# Maps client-facing session token -> (user_id, adk_session_id)
_sessions: dict[str, tuple[str, str]] = {}

_APP_NAME = "nyc_tenant_advocate"

# ── Address extraction ────────────────────────────────────────────────────────

async def extract_address(query: str) -> ParsedAddress | None:
    """
    Use Gemini to extract a structured NYC address from natural language.
    Returns None if the query cannot be parsed.
    """
    prompt = (
        "Extract the NYC address from this query. "
        "Return ONLY valid JSON with keys: house_number (string), "
        "street_name (string), borough (string — one of: Manhattan, Bronx, "
        "Brooklyn, Queens, Staten Island).\n"
        f"Query: {query}\nJSON:"
    )
    response = await _genai_client.aio.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    try:
        data = json.loads(response.text)
        return ParsedAddress(**data)
    except Exception:
        return None


# ── Advocate conversation ─────────────────────────────────────────────────────

async def generate_summary(
    address: ParsedAddress,
    violations: list[dict],
    complaints: list[dict],
    litigations: list[dict],
    risk_profile: RiskProfile,
) -> tuple[str, str]:
    """
    Create a new ADK session, send full building context, get initial summary.

    Returns:
        (summary_text, client_session_token)
    """
    user_id = str(uuid.uuid4())
    adk_session = await session_service.create_session(
        app_name=_APP_NAME,
        user_id=user_id,
    )
    client_token = str(uuid.uuid4())
    _sessions[client_token] = (user_id, adk_session.id)

    context_message = (
        f"Address: {address.house_number} {address.street_name}, {address.borough}\n\n"
        f"Risk Profile: {risk_profile.caution_level} (score: {risk_profile.score})\n"
        f"Reasons: {', '.join(risk_profile.reasons) if risk_profile.reasons else 'None'}\n\n"
        f"HPD Violations ({len(violations)} open): {violations[:5]}\n\n"
        f"DOB Complaints ({len(complaints)}): {complaints[:5]}\n\n"
        f"HPD Litigations ({len(litigations)}): {litigations[:3]}\n\n"
        "Please provide your tenant advocate analysis."
    )

    summary = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=adk_session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=context_message)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    summary = part.text

    return summary, client_token


async def chat(client_token: str, message: str) -> str:
    """
    Send a follow-up message in an existing ADK session.

    Raises:
        ValueError: if client_token is not found.
    """
    if client_token not in _sessions:
        raise ValueError(f"Session {client_token!r} not found. Call /analyze first.")

    user_id, adk_session_id = _sessions[client_token]

    reply = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=adk_session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=message)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    reply = part.text

    return reply


async def generate_voice_analysis(
    address: ParsedAddress,
    violations: list[dict],
    complaints: list[dict],
    litigations: list[dict],
    risk_profile: RiskProfile,
) -> str:
    """
    Generate a concise spoken-word summary for the voice interface.
    No ADK session is created — voice follow-up is handled by Gemini Live.

    Returns:
        summary_text suitable for reading aloud over the phone
    """
    context = (
        f"Address: {address.house_number} {address.street_name}, {address.borough}\n\n"
        f"Risk Level: {risk_profile.caution_level} (score: {risk_profile.score})\n"
        f"Reasons: {', '.join(risk_profile.reasons) if risk_profile.reasons else 'None'}\n\n"
        f"HPD Violations ({len(violations)} open): {violations[:5]}\n\n"
        f"DOB Complaints ({len(complaints)}): {complaints[:5]}\n\n"
        f"HPD Litigations ({len(litigations)}): {litigations[:3]}\n\n"
    )
    prompt = (
        "You are a pro-tenant legal advocate speaking over the phone. "
        "Based on the following building data, give a concise spoken-word analysis. "
        "Use plain sentences — no bullets, no markdown. Lead with the risk level. "
        "Flag critical violations. Mention litigation history if relevant. "
        "Keep it under 60 seconds of speech.\n\n"
        + context
    )
    response = await _genai_client.aio.models.generate_content(
        model=settings.GEMINI_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text
