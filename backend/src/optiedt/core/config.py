"""Application configuration.

Everything institutional is data, not code (ADR-003): the calendar, the slot
grid and the constraint catalogue live in the database and in
constraint_catalogue.csv, never here.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-env"
"""The published signing key. Named rather than inlined so the guard below and
the test that pins it compare against ONE value - a second literal is how a
guard silently stops matching the thing it guards."""


class InsecureConfigurationError(RuntimeError):
    """Raised when a deployment would run on the published defaults.

    A distinct type rather than a bare RuntimeError so a caller can catch this
    and nothing else: it means "your configuration is unsafe", never "something
    went wrong".
    """


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="OPTIEDT_", extra="ignore")

    # ── Database ───────────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://optiedt:optiedt@localhost:5432/optiedt"
    """⚠️ The port is 5432 by default and a developer machine may already run
    its own PostgreSQL there. `docker compose up -d` SUCCEEDS in that case -
    container healthy, mapping shown - while every connection reaches the OTHER
    server (found 2026-08-04, README.md). Set OPTIEDT_POSTGRES_PORT for the
    container and point this at the same port."""

    persistence: str = "database"
    """`database` (FR-19) or `memory`.

    ⚠️ **Configuration, never detection.** A store that fell back to memory when
    the database was unreachable would lose every run of that session while the
    application looked healthy - and FR-19 is exactly the requirement that runs
    survive a restart. `memory` has to be asked for; it exists for tests and for
    a demonstration on a machine with no database."""

    # ── Security ───────────────────────────────────────────────────
    environment: str = "development"
    """`development` or `production`. The ONLY thing it changes is whether the
    published `secret_key` default is tolerated - see `require_deployable()`.

    Defaulting to `development` is deliberate: the whole test suite, the seed
    command and `run-checks.ps1` construct `Settings()` with no environment at
    all, and a default of `production` would turn every one of them into a
    configuration error. The guard has to be opt-IN to be safe to add."""

    secret_key: str = DEFAULT_SECRET_KEY
    """⚠️ **This default is published in this repository**, so tokens signed
    with it can be forged by anyone who has read it. It is kept as a default so
    the suite and a local demonstration run with no configuration at all, and
    `require_deployable()` is what stops it reaching a deployment."""

    access_token_expire_minutes: int = 480

    # ── Solver ─────────────────────────────────────────────────────
    solver_deterministic_budget: float = 120.0
    """Deterministic time for a WHOLE run — NOT wall-clock seconds.

    ⚠️ This docstring said "per weight profile" until Phase 4 M2, and that was
    wrong: the value is passed as `PortfolioRequest.deterministic_budget`,
    which `services/portfolio.py` divides between the profiles. Read as
    per-profile, the default would mean 360 units for a three-profile run and
    blow the "< 5 min" estimate `docs/status.md` records; read as a total it
    sits beside the measured 147-150 s at total 90.

    Wall-clock bounds with parallel workers are not reproducible (ADR-011). The
    deterministic-to-wall-clock ratio is machine-dependent — calibrated
    2026-07-30, figures in docs/status.md, "Measurements". Any wall-clock
    expectation derived from this number is an estimate, never a promise.

    A budget too small to find a solution makes the solve return UNKNOWN, which
    `solver/engine.py` raises on rather than reporting as a normal result. The
    run then lands in FAILED carrying that reason - measured in Phase 4 M2 with
    a total budget of 3.
    """

    solver_wall_clock_ceiling_seconds: float = 900.0
    """Hang backstop only, never the primary bound. Reaching it is an anomaly
    to log, not a normal exit path."""

    solver_workers: int = 0
    """0 = all available. The diagnosis run overrides this to 1.

    ⚠️ **Not because CP-SAT imposes it.** This docstring said "solving under
    assumptions admits no parallelism" until 2026-08-06, and that reason died
    with the assumption mechanism (C-17, 2026-08-04). The reason now is
    **reproducibility of the VERDICT**: `max_deterministic_time` is a per-worker
    budget, so more workers do more total work and could flip an `UNKNOWN` to an
    `INFEASIBLE` between machines. A conflict report naming different rules on
    different machines would be worse than none."""

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

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    def require_deployable(self) -> None:
        """Refuse to run on the published defaults when environment=production.

        ⚠️ **A guard, not a note.** `secret_key`'s default is printed in this
        repository, so a deployment that forgets to set it signs tokens anyone
        who has read the source can forge - authentication that is present and
        worthless, which is worse than none because it looks like protection.
        Four documents recorded that risk in prose and prose stops nobody.

        Raises rather than warns. A warning on stderr at start-up is read once,
        by the person who already knows, and never by the person who deploys at
        midnight - and the failure this prevents is silent by nature.

        ⚠️ **It fires only when `environment` is `production`**, which is why
        that setting exists. The suite, the seed command and every local
        demonstration construct `Settings()` with no configuration at all; a
        guard that fired for them would be removed within a day, and a guard
        that gets removed protects nothing.
        """
        if not self.is_production:
            return
        if self.secret_key == DEFAULT_SECRET_KEY or not self.secret_key.strip():
            raise InsecureConfigurationError(
                "OPTIEDT_SECRET_KEY is unset or still the published default, and "
                "OPTIEDT_ENVIRONMENT is 'production'. Tokens signed with that key can "
                "be forged by anyone who has read this repository. Set a real secret "
                "before serving anyone but yourself."
            )
