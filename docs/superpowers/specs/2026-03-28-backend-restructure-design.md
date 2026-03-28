# NYC Tenant Advocate — Backend Restructure Design

**Date:** 2026-03-28
**Scope:** Full backend restructure to match spec, live Socrata API, Google ADK + Vertex AI, multi-turn chat

---

## 1. Goals

- Restructure `backend/` to match the spec layout in `NYC_Agent.md` exactly (using `app/` directory)
- Replace CSV-based data lookup with live Socrata API (NYC Open Data) using async parallel fetching
- Migrate from `google-genai` SDK to Google ADK + Vertex AI
- Add multi-turn chat support via client-managed ADK sessions
- Add `Dockerfile` for Cloud Run deployment
- Externalize all config via Pydantic-Settings

---

## 2. File Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI entry point & routes
│   ├── core/
│   │   ├── config.py            # Pydantic-Settings env management
│   │   └── constants.py         # Socrata dataset IDs, risk scoring weights
│   ├── services/
│   │   ├── nyc_service.py       # Async Socrata fetcher (3 datasets in parallel)
│   │   └── gemini_service.py    # ADK Agent definition, tools, session management
│   ├── models/
│   │   └── schemas.py           # All Pydantic request/response models
│   └── templates/
│       └── advocate_prompt.txt  # Tenant advocate system prompt
├── Dockerfile
├── requirements.txt
└── .env.example
```

**Deleted:** `backend/agents/`, `backend/services/data_lookup.py` (replaced by new structure)

---

## 3. Data Flow

### POST /analyze
```
{ "query": "123 Main St Brooklyn" }
        │
        ▼
ADK Agent: extract_address tool        # Gemini 2.5 Flash → { house_number, street_name, borough }
        │
        ▼
nyc_service.fetch_all(address)         # 3 async parallel Socrata queries:
    ├── HPD Violations  (wv7w-wfz2)    # active violations only
    ├── DOB Complaints  (8792-6kh6)    # open complaints
    └── HPD Litigations (63ge-vje6)   # landlord litigation history
        │
        ▼
risk scoring (inline, rule-based)      # no LLM
    ├── Class C violations → +4 pts (immediately hazardous)
    ├── Class B violations → +2 pts (hazardous)
    └── Litigations       → +3 pts
    └── thresholds: ≥5 = High, ≥2 = Moderate, <2 = Low
        │
        ▼
ADK Agent: generate_summary            # Gemini 2.5 Flash + advocate_prompt.txt
        │
        ▼
Response:
{
  "session_id": "<uuid>",
  "address": { ... },
  "violations": [ ... ],
  "complaints": [ ... ],
  "litigations": [ ... ],
  "risk_profile": { "score": int, "caution_level": str, "reasons": [...] },
  "summary": "..."
}
```

### POST /chat
```
{
  "session_id": "<uuid>",
  "message": "Can I negotiate a rent reduction?",
  "context": {
    "violations": [...],
    "complaints": [...],
    "litigations": [...],
    "risk_profile": { ... }
  }
}
        │
        ▼
ADK session resumed via session_id     # no new Socrata queries
        │
        ▼
Gemini 2.5 Flash with full context + conversation history
        │
        ▼
Response: { "reply": "...", "session_id": "<uuid>" }
```

---

## 4. ADK Agent Design (`gemini_service.py`)

- Agent defined using Google ADK `Agent` class
- Model: `gemini-2.5-flash` via Vertex AI (configurable via `GEMINI_MODEL_NAME`)
- System prompt loaded from `templates/advocate_prompt.txt`
- Session service: ADK `InMemorySessionService` keyed by `session_id` (UUID)
- `session_id` generated on `/analyze`, returned to client, passed back on `/chat`
- Context (violations, complaints, litigations, risk_profile) injected into session at creation time so follow-up questions have full building data without re-querying Socrata

**Tools registered on the agent:**
- `extract_address(query: str)` → structured address
- (Socrata fetching is NOT an ADK tool — it runs before the agent, results are passed as context)

---

## 5. Socrata Integration (`nyc_service.py`)

- Uses `httpx.AsyncClient` for async HTTP
- All 3 dataset queries fired concurrently with `asyncio.gather()`
- Query filters:
  - HPD Violations: `$where=boroid='X' AND housenumber='Y' AND streetname LIKE '%Z%' AND violationstatus='Open'`
  - DOB Complaints: address match, open status
  - HPD Litigations: address match (no status filter — all history is relevant)
- App token passed via `X-App-Token` header using `NYC_OPEN_DATA_TOKEN`
- On Socrata error: returns empty list for that dataset + sets `data_warning` flag in response

---

## 6. Configuration (`core/config.py`)

```python
class Settings(BaseSettings):
    PROJECT_ID: str
    LOCATION: str = "us-central1"
    NYC_OPEN_DATA_TOKEN: str
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    PORT: int = 8080
```

Authentication to Vertex AI via Application Default Credentials (ADC) — no API key in config.

---

## 7. Constants (`core/constants.py`)

```python
HPD_VIOLATIONS_DATASET   = "wv7w-wfz2"
DOB_COMPLAINTS_DATASET   = "8792-6kh6"
HPD_LITIGATIONS_DATASET  = "63ge-vje6"
SOCRATA_BASE_URL         = "https://data.cityofnewyork.us/resource"

RISK_SCORE_CLASS_C       = 4
RISK_SCORE_CLASS_B       = 2
RISK_SCORE_LITIGATION    = 3
RISK_THRESHOLD_HIGH      = 5
RISK_THRESHOLD_MODERATE  = 2
```

---

## 8. Pydantic Models (`models/schemas.py`)

```python
# Requests
QueryRequest:   query: str
ChatRequest:    session_id: str, message: str, context: BuildingContext

# Sub-models
ParsedAddress:  house_number, street_name, borough
RiskProfile:    score: int, caution_level: str, reasons: list[str]
BuildingContext: violations, complaints, litigations, risk_profile

# Responses
AnalyzeResponse: session_id, address, violations, complaints, litigations,
                 risk_profile, summary, data_warning: bool
ChatResponse:    reply: str, session_id: str
```

---

## 9. Error Handling

| Scenario | Behavior |
|---|---|
| Socrata API down | Return empty list for that dataset, set `data_warning: true` |
| Address not parseable | Return 400 with message |
| No violations found | Valid response — Gemini says "no active violations found" |
| Gemini/ADK error | Return 503 |
| Invalid session_id on /chat | Return 404 |

---

## 10. Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

Deployed to Cloud Run. Stateless — session state is in-memory per instance (acceptable for hackathon demo).

---

## 11. Requirements

```
fastapi
uvicorn
httpx
pydantic
pydantic-settings
google-cloud-aiplatform
google-adk
pandas  # only if needed for any data processing
```

---

## 12. .env.example

```
PROJECT_ID=your-gcp-project-id
LOCATION=us-central1
NYC_OPEN_DATA_TOKEN=your-socrata-app-token
GEMINI_MODEL_NAME=gemini-2.5-flash
PORT=8080
```
