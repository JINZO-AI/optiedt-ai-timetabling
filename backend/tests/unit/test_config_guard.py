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


# ── CORS origins ──────────────────────────────────────────────────────────
#
# ⚠️ **The hard-coded `["http://localhost:5173"]` these replace was the single
# blocker that made the application undeployable.** A browser at any other
# origin had every request refused at the preflight, and what a developer sees
# then is an opaque CORS message in the console rather than "nobody configured
# this" — so it is the kind of fault that gets diagnosed as a broken deployment.
#
# These are written the way the guard tests above are: the parsing is trivial,
# but the DEFAULT and the SHAPE of the setting are the parts a future change
# could break silently, so both are pinned.


def test_the_default_origin_is_the_vite_dev_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """A local checkout must work with no configuration at all.

    Same reasoning as `environment` defaulting to development: a setting that
    has to be set before anything runs is a setting people work around.

    ⚠️ **`delenv` as well as `_env_file=None`.** The helper's `_env_file=None`
    stops pydantic-settings reading `backend/.env`, and does NOT stop it reading
    `os.environ` - so an operator who exports OPTIEDT_CORS_ALLOWED_ORIGINS in
    their shell would turn a test about DEFAULTS red. Found by running these
    tests with the variable set; it is the same defect `tests/conftest.py`
    fixed for the assistant flag, reintroduced two files away.
    """
    monkeypatch.delenv("OPTIEDT_CORS_ALLOWED_ORIGINS", raising=False)

    assert _settings().cors_origins == ["http://localhost:5173"]


def test_no_production_url_is_baked_into_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """⚠️ The deployment supplies its own origin; this repository does not know
    it. A hard-coded production host here would be wrong for every deployment
    but the first, and would silently authorise an origin nobody chose."""
    monkeypatch.delenv("OPTIEDT_CORS_ALLOWED_ORIGINS", raising=False)

    assert all("localhost" in origin for origin in _settings().cors_origins)


def test_several_origins_are_read_from_one_comma_separated_value() -> None:
    """⚠️ Comma-separated, NOT `list[str]`.

    pydantic-settings parses a list-typed field from the environment as JSON, so
    the value would have to be written `["https://x"]` in a hosting panel —
    quoting that correctly through a shell, a Dockerfile and a web form is three
    chances to get it wrong silently. A plain string is what a person can type.
    """
    settings = _settings(
        cors_allowed_origins="https://optiedt.example.edu,https://staging.example.edu"
    )

    assert settings.cors_origins == [
        "https://optiedt.example.edu",
        "https://staging.example.edu",
    ]


def test_stray_whitespace_and_trailing_commas_are_tolerated() -> None:
    """A trailing comma in a hosting panel is not worth failing a deployment on.

    ⚠️ But an EMPTY entry would be: `""` matches no origin, and an allow list
    containing one looks exactly like a setting that was ignored.
    """
    settings = _settings(cors_allowed_origins=" https://a.example , , https://b.example ,")

    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_the_middleware_is_installed_with_the_configured_origins() -> None:
    """⚠️ The setting must actually reach the middleware.

    Verified to fire: reverting `api/main.py` to the literal list fails this,
    which is what makes it a guard rather than a restatement of the parser.
    """
    from fastapi.middleware.cors import CORSMiddleware

    from optiedt.api.main import _cors_origins, app

    installed = [m for m in app.user_middleware if m.cls is CORSMiddleware]

    assert len(installed) == 1, "exactly one CORS middleware is expected"
    assert _cors_origins == Settings().cors_origins
    assert installed[0].kwargs["allow_origins"] == _cors_origins
