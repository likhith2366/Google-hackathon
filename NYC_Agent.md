NYC Tenant Advocate Agent
Project Overview
This project is an AI-powered agent designed for a Google Gemini Hackathon. The goal is to empower NYC tenants and potential renters by analyzing public building data to identify violations, safety issues, and maintenance history.

The agent acts as a Tenant Advocate, translating complex city data into actionable advice, including suggested rent reductions or lease riders for "livable but problematic" conditions.

Technical Architecture
Framework: FastAPI (Python 3.11+)

LLM: Google Gemini 1.5 Pro (via Vertex AI or google-generativeai SDK)

Data Source: NYC Open Data (Socrata SODA API)

Deployment: Google Cloud Run (Containerized)

Configuration: Pydantic-Settings for environment management

Required File Structure
The LLM should generate code following this structure to ensure modularity and Cloud Run compatibility:

Plaintext
/
├── app/
│   ├── main.py                # FastAPI entry point & routes
│   ├── core/
│   │   ├── config.py          # Environment & Global settings
│   │   └── constants.py       # NYC Dataset IDs (HPD, DOB)
│   ├── services/
│   │   ├── nyc_service.py     # Socrata API logic (HPD/DOB fetching)
│   │   └── gemini_service.py  # Gemini Agent logic & Prompting
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   └── templates/             # (Optional) System prompts as text files
├── Dockerfile                 # Multi-stage build for Cloud Run
├── requirements.txt           # Dependencies (fastapi, uvicorn, google-cloud-aiplatform, pandas)
└── .env.example               # Template for secrets
Agent Logic & Persona
The Gemini Agent must strictly adhere to the following persona:

Role: Pro-Tenant Legal Advocate (Non-Attorney).

Tone: Empowering, protective, grounded, and concise.

Task: 1.  Ingest raw JSON data from HPD (Housing Preservation & Development) and DOB (Dept of Buildings).
2.  Identify "Critical" violations (No heat/hot water, lead paint, structural).
3.  Identify "Livable but Issue-Prone" violations (Minor leaks, common area pests, elevator delays).
4.  Actionable Output: For livable issues, suggest specific "Lease Riders" or "Rent Abatement" percentages to negotiate with the landlord.

Data Integration Points
The code must query the following NYC Open Data Sets:

HPD Violations: wv7w-wfz2 (Focus on active violations).

DOB Complaints: 8792-6kh6.

HPD Litigations: 63ge-vje6 (To see if the landlord has a history of being sued).

Environment Variables
The application must externalize these variables using pydantic-settings:

PROJECT_ID: Google Cloud Project ID.

LOCATION: GCP Region (e.g., us-central1).

NYC_OPEN_DATA_TOKEN: Socrata App Token for higher rate limits.

GEMINI_MODEL_NAME: Defaulting to gemini-1.5-pro.

Deployment Specification
Dockerfile: Must use a lightweight base image (python:3.11-slim).

Port: Must listen on the $PORT environment variable (default 8080).

Cloud Run: The agent should be stateless.