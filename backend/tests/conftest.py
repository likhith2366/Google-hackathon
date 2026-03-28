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
