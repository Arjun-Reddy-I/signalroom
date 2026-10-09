from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "SignalRoom API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./signalroom.db"

    # Security & Tokens
    SECRET_KEY: str = "signalroom-secret-key-change-this-in-production-32bytes!"
    ENCRYPTION_KEY: str = "gAAAAABlX1kZ-9X8vR3X5Z1V9X8vR3X5Z1V9X8vR3X4="
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Storage
    STORAGE_PROVIDER: str = "local"  # "local" | "s3"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 250 * 1024 * 1024  # 250MB

    # Vector Search
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # External Provider Configs
    STT_PROVIDER: str = "fallback"  # "fallback" | "whisper" | "openai"
    WHISPER_MODEL: str = "base"

    LLM_PROVIDER: str = "fallback"  # "fallback" | "openai" | "gemini"
    LLM_MODEL: str = "gpt-4o-mini"

    EMBEDDING_PROVIDER: str = "fallback"  # "fallback" | "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # API Keys
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Email
    EMAIL_PROVIDER: str = "fallback"  # "fallback" | "smtp"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "notifications@signalroom.app"
    EMAILS_FROM_NAME: str = "SignalRoom"

    # Calendar Integration
    CALENDAR_PROVIDER: str = "fallback"  # "fallback" | "google"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/settings/calendar/callback"

    # Rate Limiting & Auth Throttle
    AUTH_MAX_ATTEMPTS: int = 5
    AUTH_LOCKOUT_SECONDS: int = 900


settings = Settings()
