# NYC Tenant Advocate — Backend Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Multi-session note:** This plan is designed to be picked up across multiple sessions. Each task is self-contained. At the start of every new session: read this file, check which tasks are incomplete (unchecked boxes), read the current state of files relevant to the next task, then continue. Do NOT re-do completed tasks.

---

## Project Context

**What this is:** NYC Tenant Advocate — a Google Gemini Hackathon project. An AI agent that analyzes NYC public building data (violations, complaints, litigations) and gives pro-tenant advice.

**Repo:** `/Users/nihalajayakumar/Desktop/Projects/GoogHackathon`

**Spec:** `NYC_Agent.md` at the repo root — read it if you need full context on the agent persona and data sources.

**Design doc:** `docs/superpowers/specs/2026-03-28-backend-restructure-design.md` — read it for architectural decisions and rationale.

**Current state of the backend (before this plan is executed):**
- `backend/main.py` — old FastAPI entry point (to be deleted)
- `backend/agents/` — old address/risk/explainer agents (to be deleted)
- `backend/services/data_lookup.py` — CSV-based lookup (to be deleted)
- `backend/requirements.txt` — needs updating
- `backend/data/*.csv` — NOT used anymore; live Socrata API replaces CSVs

**What this plan builds:** A fully restructured `backend/app/` following the spec, with live Socrata API, Google ADK + Vertex AI, and multi-turn chat via client-managed sessions.

---

**Goal:** Restructure the backend to match the spec layout, replace CSV lookups with live Socrata API (async parallel), and wire up Google ADK + Vertex AI for multi-turn tenant advocate conversations.

**Architecture:** FastAPI wraps a Google ADK `Runner` backed by `InMemorySessionService`. `/analyze` fetches all three NYC datasets concurrently via `httpx.AsyncClient`, scores risk inline, creates an ADK session, and returns a session token. `/chat` resumes that session — no Socrata calls needed. Address extraction uses the `google-genai` client directly for structured JSON output.

**Tech Stack:** FastAPI, Google ADK (`google-adk`), google-genai (Vertex AI), httpx (async Socrata), Pydantic-Settings, pytest + pytest-asyncio, Cloud Run via Dockerfile.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `backend/app/__init__.py` | package marker |
| Create | `backend/app/core/__init__.py` | package marker |
| Create | `backend/app/core/config.py` | Pydantic-Settings env management |
| Create | `backend/app/core/constants.py` | Socrata dataset IDs + risk scoring weights |
| Create | `backend/app/models/__init__.py` | package marker |
| Create | `backend/app/models/schemas.py` | all Pydantic request/response models |
| Create | `backend/app/services/__init__.py` | package marker |
| Create | `backend/app/services/nyc_service.py` | async Socrata fetcher (3 datasets parallel) |
| Create | `backend/app/services/gemini_service.py` | ADK agent, session management, address extraction |
| Create | `backend/app/templates/advocate_prompt.txt` | system prompt for tenant advocate persona |
| Create | `backend/app/main.py` | FastAPI routes + inline risk scoring |
| Create | `backend/tests/__init__.py` | package marker |
| Create | `backend/tests/conftest.py` | shared pytest fixtures + settings override |
| Create | `backend/tests/test_nyc_service.py` | Socrata fetcher tests |
| Create | `backend/tests/test_gemini_service.py` | ADK + address extraction tests |
| Create | `backend/tests/test_main.py` | FastAPI integration tests |
| Create | `backend/Dockerfile` | Cloud Run container |
| Modify | `backend/requirements.txt` | updated dependencies |
| Create | `backend/.env.example` | env template |
| Delete | `backend/agents/` | replaced by new structure |
| Delete | `backend/services/data_lookup.py` | replaced by nyc_service.py |

---

## Progress Tracker

Update this table as tasks complete. In a new session, check here first.

| Task | Status | Notes |
|---|---|---|
| Task 1: Scaffold | ✅ Complete | |
| Task 2: core/ | ✅ Complete | depends on Task 1 |
| Task 3: models/schemas.py | ✅ Complete | depends on Task 1 |
| Task 4: advocate_prompt.txt | ✅ Complete | depends on Task 1 |
| Task 5: nyc_service.py | ✅ Complete | depends on Tasks 2, 3 |
| Task 6: gemini_service.py | ✅ Complete | depends on Tasks 2, 3, 4 |
| Task 7: main.py | ✅ Complete | depends on Tasks 5, 6 |
| Task 8: Dockerfile + deps | ✅ Complete | depends on Task 7 |

**Statuses:** ⬜ Not started → 🔄 In progress → ✅ Complete

---

## Resuming in a New Session

1. Read this file top to bottom
2. Check the Progress Tracker above — find the first incomplete task
3. Read the files listed under that task's **Files** section to understand current state
4. Continue from the first unchecked step in that task

**Working directory for all commands:** `backend/` (i.e. `cd /Users/nihalajayakumar/Desktop/Projects/GoogHackathon/backend`)

**Run all tests at any point with:**
```bash
cd /Users/nihalajayakumar/Desktop/Projects/GoogHackathon/backend
python -m pytest tests/ -v
```

---

## Task 1: Scaffold New Structure + Delete Old Code

**Prerequisites:** None — start here.

**Context:** The old backend uses `backend/main.py`, `backend/agents/`, and `backend/services/data_lookup.py`. All of these get deleted and replaced by the new `backend/app/` structure.

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/models/__init__.py`, `backend/app/services/__init__.py`, `backend/app/templates/` (dir), `backend/tests/__init__.py`
- Delete: `backend/agents/`, `backend/services/data_lookup.py`, `backend/main.py` (old)

- [ ] **Step 1: Create new directory structure**

```bash
cd backend
mkdir -p app/core app/models app/services app/templates tests
touch app/__init__.py app/core/__init__.py app/models/__init__.py app/services/__init__.py tests/__init__.py
```

- [ ] **Step 2: Delete old files**

```bash
rm -rf agents/ services/
rm -f main.py
```

- [ ] **Step 3: Verify structure**

```bash
find . -not -path './.git*' -not -path './data*' | sort
```

Expected output includes: `./app/`, `./app/core/`, `./app/models/`, `./app/services/`, `./app/templates/`, `./tests/`

- [ ] **Step 4: Create tests/conftest.py to mock settings for all tests**

```python
# backend/tests/conftest.py
import os
import pytest

# Set required env vars before any app module is imported
os.environ.setdefault("PROJECT_ID", "test-project")
os.environ.setdefault("LOCATION", "us-central1")
os.environ.setdefault("NYC_OPEN_DATA_TOKEN", "test-token")
os.environ.setdefault("GEMINI_MODEL_NAME", "gemini-2.5-flash")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
```

- [ ] **Step 5: Create pytest.ini so pytest-asyncio works automatically**

```ini
# backend/pytest.ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 6: Commit**

```bash
cd ..
git add -A
git commit -m "refactor: scaffold new app structure, remove old agents/ and services/"
```

---

## Task 2: core/config.py + core/constants.py

**Prerequisites:** Task 1 complete. Directory `backend/app/core/` exists with `__init__.py`.

**Context:** All environment variables are currently hardcoded inline. `config.py` centralises them via Pydantic-Settings and sets the Vertex AI env vars that ADK needs. `constants.py` holds Socrata dataset IDs and risk scoring weights used by `nyc_service.py` (Task 5) and `main.py` (Task 7).

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/constants.py`

- [ ] **Step 1: Write config.py**

```python
# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_ID: str
    LOCATION: str = "us-central1"
    NYC_OPEN_DATA_TOKEN: str
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    PORT: int = 8080


settings = Settings()

# Set Vertex AI environment variables immediately so ADK picks them up
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.LOCATION
```

- [ ] **Step 2: Write constants.py**

```python
# backend/app/core/constants.py

# Socrata dataset identifiers (NYC Open Data)
HPD_VIOLATIONS_DATASET = "wv7w-wfz2"
DOB_COMPLAINTS_DATASET = "8792-6kh6"
HPD_LITIGATIONS_DATASET = "63ge-vje6"
SOCRATA_BASE_URL = "https://data.cityofnewyork.us/resource"

# Risk scoring weights
RISK_SCORE_CLASS_C = 4   # immediately hazardous
RISK_SCORE_CLASS_B = 2   # hazardous
RISK_SCORE_LITIGATION = 3

# Risk level thresholds
RISK_THRESHOLD_HIGH = 5
RISK_THRESHOLD_MODERATE = 2
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py backend/app/core/constants.py
git commit -m "feat: add core config and constants"
```

---

## Task 3: models/schemas.py

**Prerequisites:** Task 1 complete. Directory `backend/app/models/` exists with `__init__.py`.

**Context:** Pydantic models were previously scattered across the agent files. This task centralises all request/response types. These types are imported by `nyc_service.py` (Task 5), `gemini_service.py` (Task 6), and `main.py` (Task 7).

**Files:**
- Create: `backend/app/models/schemas.py`
- Test: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_schemas.py
from app.models.schemas import (
    QueryRequest, ParsedAddress, RiskProfile,
    BuildingContext, AnalyzeResponse, ChatRequest, ChatResponse,
)


def test_query_request_requires_query():
    req = QueryRequest(query="123 Main St Brooklyn")
    assert req.query == "123 Main St Brooklyn"


def test_risk_profile_fields():
    rp = RiskProfile(score=6, caution_level="High", reasons=["2 Class C violations"])
    assert rp.score == 6
    assert rp.caution_level == "High"


def test_analyze_response_default_data_warning_false():
    addr = ParsedAddress(house_number="123", street_name="Main St", borough="Brooklyn")
    rp = RiskProfile(score=0, caution_level="Low", reasons=[])
    resp = AnalyzeResponse(
        session_id="abc",
        address=addr,
        violations=[],
        complaints=[],
        litigations=[],
        risk_profile=rp,
        summary="All clear.",
    )
    assert resp.data_warning is False


def test_chat_request_fields():
    addr = ParsedAddress(house_number="1", street_name="Broadway", borough="Manhattan")
    rp = RiskProfile(score=0, caution_level="Low", reasons=[])
    ctx = BuildingContext(violations=[], complaints=[], litigations=[], risk_profile=rp)
    req = ChatRequest(session_id="sess-1", message="Can I negotiate rent?", context=ctx)
    assert req.session_id == "sess-1"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_schemas.py -v
```

Expected: `ImportError` — `schemas` module doesn't exist yet.

- [ ] **Step 3: Write schemas.py**

```python
# backend/app/models/schemas.py
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class ParsedAddress(BaseModel):
    house_number: str
    street_name: str
    borough: str


class RiskProfile(BaseModel):
    score: int
    caution_level: str  # "High", "Moderate", "Low"
    reasons: list[str]


class BuildingContext(BaseModel):
    violations: list[dict]
    complaints: list[dict]
    litigations: list[dict]
    risk_profile: RiskProfile


class AnalyzeResponse(BaseModel):
    session_id: str
    address: ParsedAddress
    violations: list[dict]
    complaints: list[dict]
    litigations: list[dict]
    risk_profile: RiskProfile
    summary: str
    data_warning: bool = False


class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: BuildingContext


class ChatResponse(BaseModel):
    reply: str
    session_id: str
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_schemas.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add Pydantic schemas"
```

---

## Task 4: templates/advocate_prompt.txt

**Prerequisites:** Task 1 complete. Directory `backend/app/templates/` exists.

**Context:** The tenant advocate system prompt was previously hardcoded as a string in `explainer_agent.py`. Moving it to a text file makes it easy to iterate without touching Python code. `gemini_service.py` (Task 6) reads this file at startup via `Path(__file__).parent.parent / "templates" / "advocate_prompt.txt"`.

**Files:**
- Create: `backend/app/templates/advocate_prompt.txt`

- [ ] **Step 1: Write advocate_prompt.txt**

```
# backend/app/templates/advocate_prompt.txt
You are a pro-tenant legal advocate (non-attorney) specializing in NYC housing law. Your role is to help tenants and prospective renters understand building history and violation records for NYC properties.

Your tone is: empowering, protective, grounded, and concise.

When analyzing a property you will receive: the address, a risk profile, and raw data from HPD Violations, DOB Complaints, and HPD Litigations.

Your analysis must:
1. Lead with the risk level (High / Moderate / Low) in plain language.
2. Identify "Critical" violations — no heat/hot water, lead paint, structural issues, mold, vermin infestation — and flag them as serious safety concerns requiring immediate action.
3. Identify "Livable but Issue-Prone" violations — minor leaks, common area pests, elevator delays — and suggest specific remedies.
4. For livable issues, suggest concrete "Lease Riders" or "Rent Abatement" percentages (e.g., "Request a 10–15% rent abatement for persistent Class B elevator violations").
5. Interpret landlord litigation history as a signal of management practices — many cases = red flag.
6. Always advise tenants to document issues with photos and written 311 complaints.
7. Remind tenants of their right to withhold rent in escrow for Class C (immediately hazardous) violations under NYC Housing Court procedures.

For follow-up questions, use only the building data provided at the start of the conversation. Do not speculate about data you were not given.

You do not provide legal advice. For serious matters, encourage tenants to contact a housing attorney or NYC tenant advocacy organization (e.g., Housing Court Answers, Met Council on Housing).

Keep responses concise, actionable, and in plain English. Lead with the most important findings.
```

- [ ] **Step 2: Verify file exists**

```bash
cat backend/app/templates/advocate_prompt.txt
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/templates/advocate_prompt.txt
git commit -m "feat: add tenant advocate system prompt"
```

---

## Task 5: services/nyc_service.py — Async Socrata Fetcher

**Prerequisites:** Tasks 1, 2, 3 complete. `backend/app/core/config.py`, `backend/app/core/constants.py`, and `backend/app/models/schemas.py` all exist.

**Context:** The old `data_lookup.py` loaded 77MB CSV files into Pandas DataFrames. This replaces it entirely with live async HTTP calls to the NYC Open Data Socrata API. Three datasets are fetched in parallel per request using `asyncio.gather`. A `data_warning` flag is set if any dataset fetch throws an exception (network error, rate limit, etc.) — this allows the app to still respond with partial data rather than failing hard.

**Socrata datasets:**
- HPD Violations `wv7w-wfz2` — active building violations (filter: `violationstatus='Open'`)
- DOB Complaints `8792-6kh6` — Department of Buildings complaints
- HPD Litigations `63ge-vje6` — landlord lawsuit history (no status filter — all history matters)

**Files:**
- Create: `backend/app/services/nyc_service.py`
- Test: `backend/tests/test_nyc_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_nyc_service.py
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.nyc_service import fetch_all, _fetch_dataset


async def test_fetch_dataset_returns_json_on_success():
    mock_response = MagicMock()
    mock_response.json.return_value = [{"class": "C"}]
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    data, errored = await _fetch_dataset(mock_client, "wv7w-wfz2", {"$limit": 10})

    assert data == [{"class": "C"}]
    assert errored is False


async def test_fetch_dataset_returns_empty_and_true_on_error():
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Network error")

    data, errored = await _fetch_dataset(mock_client, "wv7w-wfz2", {})

    assert data == []
    assert errored is True


async def test_fetch_all_returns_all_three_datasets():
    violations = [{"class": "C"}]
    complaints = [{"complaintcategory": "ELEVATOR"}]
    litigations = [{"casetype": "HP PROCEEDING"}]

    async def fake_fetch(client, dataset_id, params):
        if dataset_id == "wv7w-wfz2":
            return violations, False
        if dataset_id == "8792-6kh6":
            return complaints, False
        if dataset_id == "63ge-vje6":
            return litigations, False

    with patch("app.services.nyc_service._fetch_dataset", side_effect=fake_fetch):
        result = await fetch_all("123", "MAIN ST", "Brooklyn")

    assert result["violations"] == violations
    assert result["complaints"] == complaints
    assert result["litigations"] == litigations
    assert result["data_warning"] is False


async def test_fetch_all_sets_data_warning_when_any_dataset_errors():
    async def fake_fetch(client, dataset_id, params):
        if dataset_id == "wv7w-wfz2":
            return [], True   # error on violations
        return [], False

    with patch("app.services.nyc_service._fetch_dataset", side_effect=fake_fetch):
        result = await fetch_all("123", "MAIN ST", "Brooklyn")

    assert result["data_warning"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_nyc_service.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 3: Write nyc_service.py**

```python
# backend/app/services/nyc_service.py
import asyncio
import httpx
from app.core.config import settings
from app.core.constants import (
    HPD_VIOLATIONS_DATASET,
    DOB_COMPLAINTS_DATASET,
    HPD_LITIGATIONS_DATASET,
    SOCRATA_BASE_URL,
)


async def _fetch_dataset(
    client: httpx.AsyncClient, dataset_id: str, params: dict
) -> tuple[list[dict], bool]:
    """Fetch one Socrata dataset. Returns (data, errored)."""
    url = f"{SOCRATA_BASE_URL}/{dataset_id}.json"
    headers = {"X-App-Token": settings.NYC_OPEN_DATA_TOKEN}
    try:
        response = await client.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json(), False
    except Exception:
        return [], True


async def fetch_all(house_number: str, street_name: str, borough: str) -> dict:
    """
    Fetch HPD violations, DOB complaints, and HPD litigations in parallel.

    Returns:
        {
            "violations": [...],
            "complaints": [...],
            "litigations": [...],
            "data_warning": bool  # True if any dataset fetch errored
        }
    """
    street_upper = street_name.upper()
    hn = house_number

    async with httpx.AsyncClient() as client:
        violations_coro = _fetch_dataset(client, HPD_VIOLATIONS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%' "
                f"AND violationstatus='Open'"
            ),
            "$limit": 100,
        })
        complaints_coro = _fetch_dataset(client, DOB_COMPLAINTS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%'"
            ),
            "$limit": 100,
        })
        litigations_coro = _fetch_dataset(client, HPD_LITIGATIONS_DATASET, {
            "$where": (
                f"housenumber='{hn}' "
                f"AND streetname LIKE '%{street_upper}%'"
            ),
            "$limit": 50,
        })

        results = await asyncio.gather(violations_coro, complaints_coro, litigations_coro)

    violations, v_err = results[0]
    complaints, c_err = results[1]
    litigations, l_err = results[2]

    return {
        "violations": violations,
        "complaints": complaints,
        "litigations": litigations,
        "data_warning": any([v_err, c_err, l_err]),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_nyc_service.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nyc_service.py backend/tests/test_nyc_service.py
git commit -m "feat: add async Socrata fetcher with parallel dataset queries"
```

---

## Task 6: services/gemini_service.py — ADK Agent + Address Extraction

**Prerequisites:** Tasks 1, 2, 3, 4 complete. `config.py`, `schemas.py`, and `advocate_prompt.txt` all exist.

**Context:** The old code used three separate agent files (`address_agent.py`, `risk_agent.py`, `explainer_agent.py`) with the `google-genai` SDK directly. This consolidates all Gemini logic into one service using Google ADK.

**Two responsibilities in this file:**
1. **Address extraction** — a single `generate_content` call with `response_mime_type="application/json"` to parse natural language into `{house_number, street_name, borough}`. Uses `google-genai` client directly (no ADK needed for a single structured call).
2. **Advocate conversation** — ADK `Runner` + `InMemorySessionService`. On `/analyze`, creates a new ADK session, sends the full building context as the first message, returns the summary + a client token. On `/chat`, resumes the existing session using the stored token — the ADK session already has the full conversation history, so no Socrata calls are needed.

**Session management:** `_sessions` dict maps `client_token (UUID)` → `(user_id, adk_session_id)`. The client_token is what gets returned to the frontend as `session_id`. This is module-level state — fine for Cloud Run single-instance (hackathon demo).

**Vertex AI auth:** `config.py` sets `GOOGLE_GENAI_USE_VERTEXAI=1`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION` as env vars when imported. ADK and google-genai both pick these up automatically. No API key needed — uses Application Default Credentials (ADC).

**Files:**
- Create: `backend/app/services/gemini_service.py`
- Test: `backend/tests/test_gemini_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_gemini_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.models.schemas import ParsedAddress, RiskProfile
from app.services.gemini_service import extract_address, generate_summary, chat


async def test_extract_address_returns_parsed_address():
    mock_response = MagicMock()
    mock_response.text = '{"house_number": "123", "street_name": "Main St", "borough": "Brooklyn"}'

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await extract_address("123 Main St Brooklyn")

    assert isinstance(result, ParsedAddress)
    assert result.house_number == "123"
    assert result.street_name == "Main St"
    assert result.borough == "Brooklyn"


async def test_extract_address_returns_none_on_bad_json():
    mock_response = MagicMock()
    mock_response.text = "I cannot parse that."

    with patch("app.services.gemini_service._genai_client") as mock_client:
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        result = await extract_address("not an address")

    assert result is None


async def test_generate_summary_returns_text_and_session_id():
    addr = ParsedAddress(house_number="1", street_name="Broadway", borough="Manhattan")
    rp = RiskProfile(score=4, caution_level="Moderate", reasons=["2 Class B violations"])

    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True
    mock_event.content.parts = [MagicMock(text="Your building has issues.")]

    async def mock_run_async(**kwargs):
        yield mock_event

    with patch("app.services.gemini_service._runner") as mock_runner, \
         patch("app.services.gemini_service.session_service") as mock_ss:
        mock_runner.run_async = mock_run_async
        mock_session = MagicMock()
        mock_session.id = "adk-session-abc"
        mock_ss.create_session = AsyncMock(return_value=mock_session)

        summary, session_id = await generate_summary(
            address=addr,
            violations=[],
            complaints=[],
            litigations=[],
            risk_profile=rp,
        )

    assert "issues" in summary
    assert session_id is not None


async def test_chat_raises_on_unknown_session():
    from app.services.gemini_service import chat
    with pytest.raises(ValueError, match="Session .* not found"):
        await chat("nonexistent-session-id", "any message")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_gemini_service.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 3: Write gemini_service.py**

```python
# backend/app/services/gemini_service.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_gemini_service.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/gemini_service.py backend/tests/test_gemini_service.py
git commit -m "feat: add ADK agent service with address extraction and multi-turn chat"
```

---

## Task 7: app/main.py — FastAPI Routes + Risk Scoring

**Prerequisites:** Tasks 1–6 all complete. `nyc_service.py` and `gemini_service.py` both exist and their tests pass.

**Context:** The old `backend/main.py` (now deleted) had a working pipeline. This rebuilds it cleanly under `app/main.py`. Risk scoring is inline (no LLM) — rule-based point system using violation classes and litigation count. The `/chat` endpoint does NOT call Socrata; it passes the message directly to `gemini_service.chat()` which resumes the ADK session.

**Note on HPD violation class field:** The Socrata API returns violation class as the field `"class"` (lowercase). Values are `"A"`, `"B"`, `"C"`. If you find this field is named differently in real API responses (e.g., `"violationclass"`), update `_compute_risk` in `main.py` accordingly.

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_main.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import ParsedAddress, RiskProfile

client = TestClient(app)

MOCK_ADDRESS = ParsedAddress(house_number="123", street_name="Main St", borough="Brooklyn")
MOCK_RISK = RiskProfile(score=4, caution_level="Moderate", reasons=["2 Class B violations"])
MOCK_DATA = {
    "violations": [{"class": "B"}],
    "complaints": [],
    "litigations": [],
    "data_warning": False,
}


def test_analyze_returns_200_with_session_id():
    with patch("app.main.extract_address", new=AsyncMock(return_value=MOCK_ADDRESS)), \
         patch("app.main.fetch_all", new=AsyncMock(return_value=MOCK_DATA)), \
         patch("app.main.generate_summary", new=AsyncMock(return_value=("Great building.", "sess-abc"))):

        resp = client.post("/analyze", json={"query": "123 Main St Brooklyn"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "sess-abc"
    assert body["summary"] == "Great building."
    assert body["risk_profile"]["caution_level"] == "Moderate"


def test_analyze_returns_400_on_unparseable_address():
    with patch("app.main.extract_address", new=AsyncMock(return_value=None)):
        resp = client.post("/analyze", json={"query": "gibberish"})

    assert resp.status_code == 400
    assert "address" in resp.json()["detail"].lower()


def test_chat_returns_200_with_reply():
    mock_context = {
        "violations": [],
        "complaints": [],
        "litigations": [],
        "risk_profile": {"score": 0, "caution_level": "Low", "reasons": []},
    }
    with patch("app.main.gemini_chat", new=AsyncMock(return_value="You can negotiate.")):
        resp = client.post("/chat", json={
            "session_id": "sess-abc",
            "message": "Can I reduce rent?",
            "context": mock_context,
        })

    assert resp.status_code == 200
    assert resp.json()["reply"] == "You can negotiate."


def test_chat_returns_404_on_unknown_session():
    with patch("app.main.gemini_chat", new=AsyncMock(side_effect=ValueError("Session 'x' not found"))):
        resp = client.post("/chat", json={
            "session_id": "unknown",
            "message": "hello",
            "context": {
                "violations": [],
                "complaints": [],
                "litigations": [],
                "risk_profile": {"score": 0, "caution_level": "Low", "reasons": []},
            },
        })

    assert resp.status_code == 404


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

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_main.py -v
```

Expected: `ImportError` — `app.main` doesn't exist yet.

- [ ] **Step 3: Write main.py**

```python
# backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.constants import (
    RISK_SCORE_CLASS_B,
    RISK_SCORE_CLASS_C,
    RISK_SCORE_LITIGATION,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MODERATE,
)
from app.models.schemas import (
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    QueryRequest,
    RiskProfile,
)
from app.services.gemini_service import (
    chat as gemini_chat,
    extract_address,
    generate_summary,
)
from app.services.nyc_service import fetch_all

app = FastAPI(title="NYC Tenant Advocate")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _compute_risk(violations: list[dict], litigations: list[dict]) -> RiskProfile:
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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: QueryRequest):
    address = await extract_address(request.query)
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Could not parse a valid NYC address from your query.",
        )

    data = await fetch_all(address.house_number, address.street_name, address.borough)
    risk_profile = _compute_risk(data["violations"], data["litigations"])

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

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_main.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all tests PASSED, no failures.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_main.py
git commit -m "feat: add FastAPI routes and risk scoring logic"
```

---

## Task 8: requirements.txt + .env.example + Dockerfile

**Prerequisites:** Task 7 complete. All app code exists and tests pass.

**Context:** The old `requirements.txt` had 5 packages and no versions. This updates it for the new stack. The Dockerfile is new — needed for Cloud Run deployment. `.env.example` documents the required env vars so anyone picking up the project knows what to configure.

**Cloud Run deployment notes:**
- Authenticate with `gcloud auth application-default login` locally, or attach a service account with `roles/aiplatform.user` on Cloud Run
- Deploy with: `gcloud run deploy nyc-tenant-advocate --source backend/ --region us-central1 --set-env-vars PROJECT_ID=...,LOCATION=us-central1,NYC_OPEN_DATA_TOKEN=...`

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write requirements.txt**

```
# backend/requirements.txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
google-adk>=1.0.0
google-genai>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Write .env.example**

```
# backend/.env.example
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
NYC_OPEN_DATA_TOKEN=your-socrata-app-token
GEMINI_MODEL_NAME=gemini-2.5-flash
PORT=8080
```

- [ ] **Step 3: Write Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

- [ ] **Step 4: Verify app starts locally**

```bash
cd backend
cp .env.example .env
# Fill in real values for PROJECT_ID, LOCATION, NYC_OPEN_DATA_TOKEN
uvicorn app.main:app --reload --port 8080
```

Expected: `INFO: Application startup complete.` with no import errors.

- [ ] **Step 5: Test /analyze end-to-end (manual)**

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "123 Main Street Brooklyn"}'
```

Expected: JSON response with `session_id`, `risk_profile`, `summary`, `violations`.

- [ ] **Step 6: Test /chat end-to-end (manual, use session_id from previous response)**

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id_from_analyze>",
    "message": "Can I negotiate a rent reduction?",
    "context": {"violations": [], "complaints": [], "litigations": [], "risk_profile": {"score": 0, "caution_level": "Low", "reasons": []}}
  }'
```

Expected: JSON with `reply` containing tenant advocate follow-up text.

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/Dockerfile
git commit -m "feat: add Dockerfile, requirements, and env template for Cloud Run deployment"
```

---

## Spec Coverage Check

| Spec Requirement | Covered By |
|---|---|
| `app/` directory structure | Task 1 |
| `core/config.py` Pydantic-Settings | Task 2 |
| `core/constants.py` dataset IDs | Task 2 |
| `models/schemas.py` | Task 3 |
| `templates/advocate_prompt.txt` | Task 4 |
| `services/nyc_service.py` Socrata API | Task 5 |
| `services/gemini_service.py` ADK agent | Task 6 |
| Async parallel 3-dataset fetch | Task 5 |
| `app/main.py` FastAPI routes | Task 7 |
| POST /analyze | Task 7 |
| POST /chat (multi-turn, no extra API calls) | Task 7 |
| Risk scoring (Class B/C + litigations) | Task 7 |
| Vertex AI + ADC auth | Task 6 (config.py sets env vars) |
| Client-managed session_id | Task 6 |
| `data_warning` flag on partial fetch | Task 5 |
| Dockerfile + Cloud Run | Task 8 |
| `.env.example` | Task 8 |
