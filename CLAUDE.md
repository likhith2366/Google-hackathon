# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BeforeYouSign** — an AI-powered NYC tenant advocate that analyzes public building data (HPD violations, DOB complaints, HPD litigations) and uses Google Gemini to generate pro-tenant summaries and enable follow-up chat. Built for the Google Gemini Hackathon.

## Development Commands

### Backend (FastAPI)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn app.main:app --reload --port 8080

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_main.py -v

# Run a single test by name
python -m pytest tests/test_main.py::test_analyze_returns_200_with_session_id -v
```

### Frontend (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (http://localhost:5173)
npm run dev

# Lint
npm run lint

# Build for production
npm run build
```

### Docker

```bash
cd backend
docker build -t nyc-tenant-advocate .
docker run -p 8080:8080 -e PROJECT_ID=your-project -e LOCATION=us-central1 nyc-tenant-advocate
```

### Deploy to Cloud Run

```bash
gcloud run deploy nyc-tenant-advocate \
  --source backend/ \
  --region us-central1 \
  --allow-unauthenticated \
  --timeout 3600 \
  --min-instances 1 \
  --set-env-vars PROJECT_ID=your-project,LOCATION=us-central1,GEMINI_LIVE_MODEL_NAME=gemini-2.0-flash-live-001
```

- `--timeout 3600` — required for long-lived Twilio WebSocket connections
- `--min-instances 1` — prevents cold starts from dropping active calls
- `--allow-unauthenticated` — Twilio webhooks must reach the service from outside GCP
- Set `TWILIO_AUTH_TOKEN` as a Secret Manager secret and reference via `--set-secrets`

## Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:

| Variable | Description |
|---|---|
| `PROJECT_ID` | GCP project ID for Vertex AI |
| `LOCATION` | GCP region (e.g., `us-central1`) |
| `NYC_OPEN_DATA_KEY_ID` | Socrata app key ID |
| `NYC_OPEN_DATA_KEY_SECRET` | Socrata app key secret |
| `GEMINI_MODEL_NAME` | Defaults to `gemini-2.5-flash` |
| `PORT` | Defaults to `8080` |

Frontend API URL is configured via `frontend/.env.local` → `VITE_API_URL` (defaults to `http://localhost:8080`).

## Architecture

### Request Flow: `/analyze`

```
User query → Gemini LLM (extract address) → Socrata API [3 parallel requests]
  → HPD Violations, DOB Complaints, HPD Litigations
  → Risk scoring (_compute_risk in main.py)
  → Gemini ADK agent (generate_summary) → AnalyzeResponse + session_id
```

### Request Flow: `/chat`

```
User message + session_id → ADK session lookup → Gemini continuation → reply
```

### Session Management

Sessions are ADK `InMemorySessionService` instances. The `/analyze` endpoint creates a session and returns a UUID `session_id`. The `/chat` endpoint uses that ID to continue the conversation. Sessions are in-memory only — appropriate for Cloud Run with request affinity.

### Risk Scoring (backend/app/main.py `_compute_risk`)

- Class C violation: +4 pts
- Class B violation: +2 pts
- Litigation record: +3 pts
- Score ≥5 → High, ≥2 → Moderate, <2 → Low

### NYC Open Data (Socrata) Dataset IDs

Defined in `backend/app/core/constants.py`:
- HPD Violations: `wvxf-dwi5`
- DOB Complaints: `eabe-havv`
- HPD Litigations: `59kj-x8nc`

### Key Files

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI routes, CORS, risk computation |
| `backend/app/services/gemini_service.py` | Gemini ADK agent, address extraction, session management |
| `backend/app/services/nyc_service.py` | Async Socrata API fetching (httpx, basic auth) |
| `backend/app/core/config.py` | Pydantic Settings for env vars |
| `backend/app/templates/advocate_prompt.txt` | System prompt defining the pro-tenant advocate persona |
| `frontend/src/App.tsx` | Main state machine (idle → loading → result/error) |
| `frontend/src/api.ts` | Fetch client for `/analyze` and `/chat` |

### Frontend State

`App.tsx` manages: `idle | loading | result | error`. Session ID is persisted in `localStorage` to survive page reload. A new search resets the session.
