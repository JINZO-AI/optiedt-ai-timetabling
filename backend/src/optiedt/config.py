"""Runtime configuration, read from environment variables prefixed with ``OPTIEDT_``."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    """The configuration is unsafe or inconsistent for the selected environment."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPTIEDT_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"

    database_url: str = "postgresql+psycopg://optiedt:optiedt@localhost:5432/optiedt"
    database_pool_size: int = Field(default=10, ge=1, le=100)

    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    public_base_url: str = "http://localhost:5173"
    """Origin users reach the application at; used to build calendar feed links."""

    session_cookie_name: str = "optiedt_session"
    session_cookie_secure: bool = False
    session_idle_minutes: int = Field(default=120, ge=5)
    session_absolute_hours: int = Field(default=12, ge=1)

    login_max_failures: int = Field(default=5, ge=1)
    login_window_minutes: int = Field(default=15, ge=1)
    login_lockout_minutes: int = Field(default=15, ge=1)

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)

    worker_lease_seconds: int = Field(default=60, ge=10)
    worker_heartbeat_seconds: int = Field(default=10, ge=1)
    worker_poll_seconds: float = Field(default=2.0, gt=0)
    run_max_attempts: int = Field(default=2, ge=1)

    solver_workers: int = Field(default=0, ge=0)
    """CP-SAT search workers; 0 uses every available core."""
    solver_max_time_limit_seconds: int = Field(default=3600, ge=10)

    assistant_provider: Literal["disabled", "anthropic", "openai_compatible"] = "disabled"
    assistant_api_key: SecretStr | None = None
    assistant_model: str = ""
    assistant_base_url: str = ""
    assistant_timeout_seconds: float = Field(default=45.0, gt=0)

    metrics_enabled: bool = True

    @model_validator(mode="after")
    def _check_production(self) -> Settings:
        if self.environment != "production":
            return self
        problems = []
        if not self.session_cookie_secure:
            problems.append("OPTIEDT_SESSION_COOKIE_SECURE must be true")
        if not self.public_base_url.startswith("https://"):
            problems.append("OPTIEDT_PUBLIC_BASE_URL must be an https:// origin")
        if "optiedt:optiedt@" in self.database_url:
            problems.append("OPTIEDT_DATABASE_URL uses the development password")
        if self.assistant_provider != "disabled" and not self.assistant_model:
            problems.append("OPTIEDT_ASSISTANT_MODEL is required when the assistant is enabled")
        if problems:
            raise ConfigurationError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
