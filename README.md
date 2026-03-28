# BeforeYouSign

An AI-powered NYC tenant advocate that analyzes public building data and gives renters the information they need before signing a lease.

Built for the Google Gemini Hackathon.

**Contributor:** Yashwanth Kasanneni

---

## What It Does

BeforeYouSign lets you enter any NYC address and instantly get:

- A plain-English summary of HPD violations, DOB complaints, and litigation history
- A risk score (Low / Moderate / High) based on violation severity
- Actionable advice — suggested rent abatements or lease riders for problematic conditions
- A follow-up chat with the AI advocate to dig deeper

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11+) |
| LLM | Google Gemini 2.5 Flash via Google ADK |
| Voice | Gemini Live API + Twilio Media Streams |
| Data | NYC Open Data (Socrata SODA API) |
| Frontend | React + Vite + TypeScript |
| Deployment | Google Cloud Run |

---

## Architecture

### `/analyze` Flow

```
User query → Gemini (extract address) → Socrata API [3 parallel requests]
  → HPD Violations, DOB Complaints, HPD Litigations
  → Risk scoring → Gemini ADK agent (generate_summary)
  → AnalyzeResponse + session_id
```

### `/chat` Flow

```
User message + session_id → ADK session lookup → Gemini continuation → reply
```

### Risk Scoring

| Condition | Points |
|---|---|
| Class C violation | +4 |
| Class B violation | +2 |
| Litigation record | +3 |

Score ≥ 5 → **High** · Score ≥ 2 → **Moderate** · Score < 2 → **Low**

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI routes, CORS, risk computation
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings for env vars
│   │   │   └── constants.py         # NYC Open Data dataset IDs
│   │   ├── services/
│   │   │   ├── gemini_service.py    # Gemini ADK agent, address extraction, sessions
│   │   │   ├── nyc_service.py       # Async Socrata API fetching
│   │   │   └── voice_bridge.py      # Twilio ↔ Gemini Live WebSocket bridge
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic request/response models
│   │   └── templates/
│   │       └── advocate_prompt.txt  # Pro-tenant advocate system prompt
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main state machine (idle → loading → result/error)
│   │   └── api.ts                   # Fetch client for /analyze and /chat
│   └── package.json
└── CLAUDE.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- GCP project with Vertex AI enabled
- Twilio account (for voice feature)

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Run dev server
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server (http://localhost:5173)
npm run dev
```

### Environment Variables

| Variable | Description |
|---|---|
| `PROJECT_ID` | GCP project ID for Vertex AI |
| `LOCATION` | GCP region (e.g., `us-central1`) |
| `NYC_OPEN_DATA_KEY_ID` | Socrata app key ID |
| `NYC_OPEN_DATA_KEY_SECRET` | Socrata app key secret |
| `GEMINI_MODEL_NAME` | Defaults to `gemini-2.5-flash` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token (voice feature) |
| `PORT` | Defaults to `8080` |

Frontend API URL: set `VITE_API_URL` in `frontend/.env.local` (defaults to `http://localhost:8080`).

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## Deploying to Cloud Run

```bash
gcloud run deploy nyc-tenant-advocate \
  --source backend/ \
  --region us-central1 \
  --allow-unauthenticated \
  --timeout 3600 \
  --min-instances 1 \
  --set-env-vars PROJECT_ID=your-project,LOCATION=us-central1
```

> `--timeout 3600` is required for long-lived Twilio WebSocket connections.
> Store `TWILIO_AUTH_TOKEN` in Secret Manager and reference it via `--set-secrets`.

---

## NYC Open Data Sources

| Dataset | ID |
|---|---|
| HPD Violations | `wvxf-dwi5` |
| DOB Complaints | `eabe-havv` |
| HPD Litigations | `59kj-x8nc` |

---

## License

See [LICENSE](LICENSE).
