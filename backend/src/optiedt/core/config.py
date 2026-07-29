"""Application configuration.

Everything institutional is data, not code (ADR-003): the calendar, the slot
grid and the constraint catalogue live in the database and in
constraint_catalogue.csv, never here.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPTIEDT_", extra="ignore")

    # ── Database ───────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://optiedt:optiedt@localhost:5432/optiedt"

    # ── Security ───────────────────────────────────────────────────
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 480

    # ── Solver ─────────────────────────────────────────────────────
    solver_deterministic_budget: float = 120.0
    """Deterministic time per weight profile — NOT wall-clock seconds.

    Wall-clock bounds with parallel workers are not reproducible (ADR-011).
    ⚠️ The deterministic-to-wall-clock ratio is machine-dependent and must be
    calibrated on the reference instance; until then any wall-clock expectation
    derived from this number is a guess. See docs/status.md, "Measurements".
    """

    solver_wall_clock_ceiling_seconds: float = 900.0
    """Hang backstop only, never the primary bound. Reaching it is an anomaly
    to log, not a normal exit path."""

    solver_workers: int = 0
    """0 = all available. The diagnosis run overrides this to 1, which CP-SAT
    imposes: solving under assumptions admits no parallelism."""

    solver_seed: int = 42
    """Recorded with every run. Reproducibility is an acceptance criterion."""

    # ── Assistant ──────────────────────────────────────────────────
    assistant_enabled: bool = False
    """Off by default. Everything must work with it off — generation, scoring,
    ranking, comparison, regeneration and publication all remain available, and
    only text disappears. Turning it off is how FR-22/FR-25 degraded mode is
    tested."""

    assistant_base_url: str = ""
    assistant_api_key: str = ""
    assistant_model: str = ""
    assistant_timeout_seconds: float = 10.0
    """Beyond this the computed form is displayed instead."""

    # ── Instance ───────────────────────────────────────────────────
    instance_path: str = "../data/instance"
    constraint_catalogue_path: str = "../data/instance/constraint_catalogue.csv"
    """Authority for H/S codes, default weights and XHSTT references."""
