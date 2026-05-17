"""Application configuration loaded from environment variables."""
import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
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
    # Stored as a raw string because pydantic-settings JSON-decodes list[str]
    # envvars inside its env source, before any field validator runs. That
    # makes CSV unusable as list[str] — `CORS_ORIGINS=http://a,http://b`
    # raises JSONDecodeError. We keep the env var ergonomic (CSV or JSON list)
    # and expose the parsed list through the `cors_origins` property.
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_raw.strip()
        if raw.startswith("["):
            return json.loads(raw)
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
