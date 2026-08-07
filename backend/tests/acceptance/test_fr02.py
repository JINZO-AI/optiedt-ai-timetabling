"""FR-2 — a teacher declares availability on a weekly grid.

    Acceptance criterion (docs/testing-strategy.md §4), as reworded by
    project-owner decision on 2026-08-07:
    "Completed unaided by a user who had not seen it."

⚠️ **The criterion itself is not automatable and this file does not pretend to
automate it.** Whether a person completes the grid unaided was settled by the
walkthrough recorded in `docs/demonstration.md` §2 — with its limitations
written down there, including that no time was measured. What a test *can*
establish is the half a stopwatch cannot: that the capability the walkthrough
exercised is genuinely **reachable by a teacher**, over the same HTTP path the
screen uses, with the properties the protocol asks the participant to notice.

**Real tokens, no dependency override**, for the same reason `test_fr11.py`
uses them: FR-2 is about what a *teacher* can do with their own grid, and
overriding `current_user` would test the override rather than the path. The
person in charge writing any teacher's grid is FR-11's business and is tested
there; `tests/unit/test_availability_api.py` covers the replace-wholesale rule
in isolation. This file asserts neither again.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.services.users import InMemoryUserStore

pytestmark = pytest.mark.acceptance

PASSWORD = "acceptance-password"
TEACHER = "T001"


@pytest.fixture(scope="module")
def users() -> InMemoryUserStore:
    """One teacher, hashed ONCE for the module — bcrypt is deliberately slow."""
    store = InMemoryUserStore()
    store.create(User(id="u1", username="t001", role=UserRole.TEACHER, teacher=TEACHER), PASSWORD)
    return store


@pytest.fixture
def teacher(users: InMemoryUserStore) -> Iterator[TestClient]:
    for cached in (deps.get_settings, deps.get_instance, deps.get_availability_store):
        cached.cache_clear()
    app.dependency_overrides[deps.get_user_store] = lambda: users
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/token", data={"username": "t001", "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_a_teacher_reaches_the_grid_by_signing_in(teacher: TestClient) -> None:
    """The path the walkthrough took: sign in, then read your own grid.

    Not `GET /api/teachers/T001/...` with an overridden user — which teacher the
    caller is comes from the TOKEN, and that is the line FR-11 draws and FR-2
    depends on.
    """
    response = teacher.get(f"/api/teachers/{TEACHER}/availability", headers=_auth(teacher))

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)


def test_the_whole_week_is_available_in_one_request(teacher: TestClient) -> None:
    """ "The whole week on one screen" is part of what makes the grid fillable.

    The instance is sent whole (`InstanceOut`), so the grid needs no second
    request and no paging to render every day and every period.
    """
    slots = teacher.get("/api/instance", headers=_auth(teacher)).json()["slots"]

    days = {s["dayIndex"] for s in slots}
    periods = {s["periodIndex"] for s in slots}
    assert len(days) >= 5, f"a working week needs at least five days, got {sorted(days)}"
    assert len(periods) >= 4, f"expected several periods a day, got {sorted(periods)}"
    assert len(slots) == len(days) * len(periods), (
        "the grid must be a full rectangle of day x period, or a screen cannot "
        "render it as one table"
    )


def test_closed_slots_are_marked_so_the_grid_can_withhold_them(teacher: TestClient) -> None:
    """A closed slot must be identifiable as data, never inferred by the screen.

    ⚠️ **This is invariant 7.** The interface reads `is_open` and must never
    special-case a closed day of its own accord (ADR-003) — so the criterion's
    "closed slots not offered" is only honest if the payload says which they
    are. The reference instance closes Saturday afternoon, which is exactly
    what `docs/demonstration.md` §2 asks the participant whether they noticed.
    """
    slots = teacher.get("/api/instance", headers=_auth(teacher)).json()["slots"]

    closed = [s for s in slots if not s["isOpen"]]
    assert closed, "the reference instance closes Saturday afternoon; none was marked closed"
    assert all(s["isOpen"] in (True, False) for s in slots), "every slot must state is_open"


def test_a_generated_declaration_is_distinguishable_from_the_teachers_own(
    teacher: TestClient,
) -> None:
    """§2 asks whether the participant understood that grey cells are generated.

    They can only understand it if the application says so. `source` is what
    carries that, and a grid that dropped it would show a teacher rows they
    never entered with nothing to mark them as someone else's work.
    """
    headers = _auth(teacher)
    rows = teacher.get(f"/api/teachers/{TEACHER}/availability", headers=headers).json()

    assert rows, "T001 carries generated rows in the reference instance"
    assert {r["source"] for r in rows} == {"SYNTHETIC"}


def test_a_teacher_completes_the_grid_and_it_is_recorded_as_theirs(
    teacher: TestClient,
) -> None:
    """The act the criterion is about: declare unavailability, save, read back.

    The two slots are the ones `docs/demonstration.md` §1 step 3 uses, so the
    scripted demonstration and the acceptance test exercise the same thing.
    """
    headers = _auth(teacher)

    saved = teacher.put(
        f"/api/teachers/{TEACHER}/availability",
        json={
            "semester": 2,
            "cells": [
                {"slot": 0, "state": "UNAVAILABLE"},
                {"slot": 14, "state": "UNAVAILABLE"},
            ],
        },
        headers=headers,
    )

    assert saved.status_code == 200, saved.text
    assert [r["slot"] for r in saved.json()] == [0, 14]
    assert {r["source"] for r in saved.json()} == {"TEACHER"}

    # Read back through a fresh request: what was saved is what a teacher sees
    # next time, which is the whole point of saving.
    assert teacher.get(f"/api/teachers/{TEACHER}/availability", headers=headers).json() == (
        saved.json()
    )
