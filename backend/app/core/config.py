"""Application configuration loaded from environment variables."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application -----------------------------------------------------
    environment: str = "development"
    secret_key: str = "change_me_in_production"

    # ---- Database --------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://portal:portal_dev_password@localhost:5432/portal"
    )

    # ---- Redis -----------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ---- Evolution API ---------------------------------------------------
    evolution_base_url: str = "http://localhost:8080"
    evolution_api_key: str = "change_me"

    # URL Evolution should use to call back into THIS backend (reachable from
    # within the docker network). In dev with docker-compose, the backend
    # service name is "backend".
    public_backend_url: str = "http://backend:8000"

    # ---- JWT -------------------------------------------------------------
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ---- CORS ------------------------------------------------------------
    # Accepts CSV (CORS_ORIGINS=http://a,http://b) or JSON list. CSV is the
    # ergonomic form for .env files on prod VMs where the portal is reached
    # by IP (e.g. http://192.168.0.128:3000).
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                # Let pydantic handle JSON parsing.
                return s
            return [item.strip() for item in s.split(",") if item.strip()]
        return v


settings = Settings()
