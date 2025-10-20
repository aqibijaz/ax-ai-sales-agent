from typing import Literal, Optional
from pathlib import Path
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    ENV: Literal["development", "staging", "production"] = Field("development")
    PORT: int = Field(8000)
    ENVIRONMENT: Literal["development", "staging", "production"] = Field("development")

    # Essentials to run basic API + state + DB
    OPENAI_API_KEY: str = Field("dummy")
    DATABASE_URL: str
    REDIS_URL: str

    # Optional for later steps (don’t block startup)
    GOOGLE_CALENDAR_CREDENTIALS: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    AIRTABLE_TABLE_NAME: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None

try:
    settings = Settings()
except ValidationError as e:
    print("❌ Env validation failed:\n", e.json(indent=2))
    raise
