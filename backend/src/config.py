"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Resume Crafter"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # Database
    database_url: PostgresDsn = "postgresql+asyncpg://postgres:postgres@localhost:5432/resume_crafter"  # type: ignore[assignment]

    # Redis (for ARQ and rate limiting)
    redis_url: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "resume_crafter"

    # JWT Authentication
    jwt_secret_key: SecretStr = SecretStr("change-me-in-production-use-strong-key")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # LLM Provider Configuration
    # Options: "ollama" (local), "groq" (cloud), "openrouter" (cloud - many models)
    llm_provider: Literal["ollama", "groq", "openrouter"] = "openrouter"

    # Ollama settings (local)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "gemma3:4b"

    # Groq settings (cloud - fast, free tier)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenRouter settings (cloud - access to many models)
    # API key from environment variable OPENROUTER_API_KEY
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-3-4b-it:free"  # Free Gemma 3 4B

    # GitHub API settings (for project enrichment)
    # Get a token from https://github.com/settings/tokens (no scopes needed for public repos)
    github_token: str | None = None

    # Embedding Model
    embedding_model: str = "all-MiniLM-L6-v2"  # 384 dimensions, fast
    embedding_dimensions: int = 384

    # File Upload
    max_upload_size_mb: int = 10
    allowed_file_types: list[str] = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/png", "image/jpeg"]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Agent Pipeline Configuration
    # When True, uses multi-agent system with validation and refinement
    # When False, uses direct LLM extraction (legacy mode)
    use_agent_pipeline: bool = True
    agent_max_refinements: int = 3

    # CORS - set to "*" to allow all origins in development
    cors_origins_str: str = "*"

    # LinkedIn Scraper Configuration
    # Get li_at cookie from: Browser DevTools > Application > Cookies > linkedin.com
    linkedin_session_cookie: str | None = None

    # SMTP Email Configuration (for outreach)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_name: str = "Resume Crafter"

    # Scheduling Configuration
    scheduling_provider: str = "calcom"
    scheduling_link: str | None = None

    # Automation Rate Limits
    max_applications_per_day: int = 35
    min_application_delay_seconds: int = 300  # 5 minutes

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins - use '*' for all origins in development."""
        if self.cors_origins_str.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
