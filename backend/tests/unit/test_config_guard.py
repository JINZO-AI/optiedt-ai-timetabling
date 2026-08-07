"""The production guard on the published secret key.

⚠️ **Verified to FIRE before being relied on**, which is this project's standing
rule for a guard — the same discipline the eighth, ninth, tenth and eleventh
import contracts were held to, and the reason `run-checks.ps1`'s database step
was found reporting `[ok]` over 38 skipped tests.

The failure this prevents is silent by nature: `secret_key`'s default is printed
in this repository, so a deployment that forgets to set it signs tokens anyone
who has read the source can forge. Authentication would be present and
worthless, which is worse than absent because it looks like protection.
"""

from __future__ import annotations

import pytest

from optiedt.core.config import (
    DEFAULT_SECRET_KEY,
    InsecureConfigurationError,
    Settings,
)


def _settings(**overrides: object) -> Settings:
    """Settings built from explicit values only.

    `_env_file=None` matters: without it pydantic-settings reads the developer's
    real `backend/.env`, and a test asserting on defaults would pass or fail
    according to a file it does not control.
    """
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_development_tolerates_the_published_default() -> None:
    """The guard must not fire for the suite, the seed command or a demo.

    A guard that broke every local run would be removed within a day, and a
    guard that gets removed protects nothing. This is why `environment` exists
    and why it defaults to development.
    """
    settings = _settings()

    assert settings.environment == "development"
    assert settings.secret_key == DEFAULT_SECRET_KEY
    settings.require_deployable()  # must not raise


def test_production_refuses_the_published_default() -> None:
    """THE test. Verified to fire, not assumed to."""
    settings = _settings(environment="production")

    with pytest.raises(InsecureConfigurationError) as raised:
        settings.require_deployable()

    message = str(raised.value)
    assert "OPTIEDT_SECRET_KEY" in message, "the message must name the setting to change"
    assert "forged" in message, "the message must say what goes wrong, not merely that it did"


def test_production_refuses_an_empty_secret() -> None:
    """Blank is not a secret. Setting the variable to "" would otherwise read
    as "configured" while being strictly worse than the default."""
    with pytest.raises(InsecureConfigurationError):
        _settings(environment="production", secret_key="   ").require_deployable()


def test_production_accepts_a_real_secret() -> None:
    """The guard must let a correctly configured deployment through - otherwise
    it is not a guard, it is a wall."""
    _settings(environment="production", secret_key="a-real-secret").require_deployable()


@pytest.mark.parametrize("value", ["production", "PRODUCTION", " Production "])
def test_the_environment_is_read_case_and_whitespace_insensitively(value: str) -> None:
    """`OPTIEDT_ENVIRONMENT=Production` must not silently disable the guard.

    A setting that protects only on an exact lowercase match is a setting that
    fails open, and it fails open in exactly the deployment that took the
    trouble to set it.
    """
    with pytest.raises(InsecureConfigurationError):
        _settings(environment=value).require_deployable()
