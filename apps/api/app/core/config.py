from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SECRET = "signalroom-secret-key-change-this-in-production-32bytes!"
_DEFAULT_ENCRYPTION = "gAAAAABlX1kZ-9X8vR3X5Z1V9X8vR3X5Z1V9X8vR3X4="


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "SignalRoom API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @model_validator(mode="after")
    def reject_default_secrets_in_production(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == _DEFAULT_SECRET:
                raise ValueError(
                    "SECRET_KEY must be changed from the default value in production. "
                    "Set a strong random SECRET_KEY in your environment or .env file."
                )
            if self.ENCRYPTION_KEY == _DEFAULT_ENCRYPTION:
                raise ValueError(
                    "ENCRYPTION_KEY must be changed from the default value in production."
                )
        self.DATABASE_URL = self._resolve_sqlite_url(self.DATABASE_URL)
        self.UPLOAD_DIR = self._resolve_path(self.UPLOAD_DIR)
        self.CHROMA_PERSIST_DIR = self._resolve_path(self.CHROMA_PERSIST_DIR)
        return self

    @staticmethod
    def _resolve_path(value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else API_ROOT / path)

    @staticmethod
    def _resolve_sqlite_url(value: str) -> str:
        prefix = "sqlite+aiosqlite:///"
        if not value.startswith(prefix):
            return value
        path = Path(value[len(prefix):])
        if not path.is_absolute():
            path = API_ROOT / path
        return f"{prefix}{path.resolve().as_posix()}"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./signalroom.db"

    # Security & Tokens
    SECRET_KEY: str = "signalroom-secret-key-change-this-in-production-32bytes!"
    ENCRYPTION_KEY: str = "gAAAAABlX1kZ-9X8vR3X5Z1V9X8vR3X5Z1V9X8vR3X4="
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — stored as a plain comma-separated string to avoid .env parsing issues
    # e.g.  CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"

    @property
    def CORS_ORIGINS(self) -> list[str]:  # noqa: N802
        return [o.strip() for o in self.CORS_ORIGINS_STR.split(",") if o.strip()]

    # Storage
    STORAGE_PROVIDER: str = "local"  # "local" | "s3"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 250 * 1024 * 1024  # 250MB

    # Vector Search
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # External Provider Configs
    STT_PROVIDER: str = "fallback"  # "fallback" | "whisper"
    WHISPER_MODEL: str = "base"  # "tiny", "base", "small", "medium"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"

    LLM_PROVIDER: str = "fallback"  # "fallback" | "ollama" | "openai" | "gemini"
    LLM_MODEL: str = "llama3"  # model name for ollama; for gemini use "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_LLM_MODEL: str = "gemini-2.5-flash"  # fast, capable, free-tier available

    EMBEDDING_PROVIDER: str = "fallback"  # "fallback" | "sentence_transformers" | "openai"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # API Keys (optional — fallback providers used when empty)
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
