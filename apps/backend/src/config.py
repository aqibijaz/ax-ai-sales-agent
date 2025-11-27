from typing import Literal, Optional
from pathlib import Path
from pydantic import Field, ValidationError, field_validator
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
    OPENAI_MODEL: str = Field(default="gpt-4o")
    DATABASE_URL: str
    REDIS_URL: str

    # Optional for later steps (don't block startup)
    GOOGLE_CALENDAR_CREDENTIALS_JSON: Optional[str] = None
    GOOGLE_CALENDAR_ID: Optional[str] = Field(default="primary")
    
    # SMTP Email Configuration (Gmail)
    SMTP_HOST: Optional[str] = Field(default="smtp.gmail.com")
    SMTP_PORT: Optional[int] = Field(default=587)
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = Field(default="AccellionX Team")
    SMTP_USE_TLS: bool = Field(default=True)
    
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    AIRTABLE_TABLE_NAME: Optional[str] = None
    
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    # New additions
    ADMIN_DASHBOARD_URL: str = Field(default="http://localhost:3000/admin")
    DEFAULT_TIMEZONE: str = Field(default="Asia/Karachi")
    DEFAULT_MEETING_DURATION_MINUTES: int = Field(default=60)
    MAX_CONVERSATION_HISTORY: int = Field(default=50)
    CONVERSATION_TIMEOUT_HOURS: int = Field(default=24)
    HOT_LEAD_SCORE: int = Field(default=80)
    WARM_LEAD_SCORE: int = Field(default=50)
    
    # ✅ Add this validator to convert relative path to absolute
    @field_validator('GOOGLE_CALENDAR_CREDENTIALS_JSON', mode='after')
    @classmethod
    def resolve_credentials_path(cls, v):
        """Convert relative path to absolute path"""
        if v and not Path(v).is_absolute():
            # Make path relative to BASE_DIR (backend folder)
            absolute_path = BASE_DIR / v
            if absolute_path.exists():
                return str(absolute_path)
            else:
                print(f"⚠️  Warning: Google Calendar credentials file not found at: {absolute_path}")
        return v

try:
    settings = Settings()
except ValidationError as e:
    print("❌ Env validation failed:\n", e.json(indent=2))
    raise