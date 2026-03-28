import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_ID: str
    LOCATION: str = "us-central1"
    NYC_OPEN_DATA_TOKEN: str = ""
    NYC_OPEN_DATA_KEY_ID: str = ""
    NYC_OPEN_DATA_KEY_SECRET: str = ""
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_LIVE_MODEL_NAME: str = "gemini-2.0-flash-live-001"
    TWILIO_AUTH_TOKEN: str = ""
    PORT: int = 8080


settings = Settings()

# Set Vertex AI environment variables immediately so ADK picks them up
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = settings.PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = settings.LOCATION
