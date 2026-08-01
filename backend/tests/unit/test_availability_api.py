"""FR-2's write side: a teacher's declaration replaces the generated one.

The behaviour worth pinning is not "a PUT stores rows" but the two rules that
keep a generated declaration honest (docs/domain-model.md): a real declaration
is marked TEACHER rather than SYNTHETIC, and it replaces the teacher's
generated rows **wholesale**, so a slot left free can withdraw one.
"""

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from optiedt.api.deps import get_availability_store, get_instance, get_settings
from optiedt.api.main import app
from optiedt.domain.entities import Availability
from optiedt.domain.enums import AvailabilityState, DeclarationSource
from optiedt.domain.instance import Instance
from optiedt.services.availability import (
    InMemoryAvailabilityStore,
    apply_declarations,
    build_declaration,
    effective_availability,
)


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_instance.cache_clear()
    get_availability_store.cache_clear()
    return TestClient(app)


def _a_teacher_with_generated_rows(client: TestClient) -> str:
    payload = client.get("/api/instance").json()
    # The instance ships 157 SYNTHETIC rows covering 41 of 44 teachers; pick
    # one deterministically rather than assuming an id.
    for teacher in payload["teachers"]:
        rows = client.get(f"/api/teachers/{teacher['id']}/availability").json()
        if rows:
            return str(teacher["id"])
    raise AssertionError("no teacher carries a generated declaration")


def test_unknown_teacher_is_404(client: TestClient) -> None:
    assert client.get("/api/teachers/nobody/availability").status_code == 404


def test_generated_rows_are_visible_and_marked_synthetic(client: TestClient) -> None:
    teacher = _a_teacher_with_generated_rows(client)
    rows = client.get(f"/api/teachers/{teacher}/availability").json()
    assert rows
    assert {r["source"] for r in rows} == {"SYNTHETIC"}
    assert {r["state"] for r in rows} == {"UNAVAILABLE"}


def test_a_declaration_replaces_the_generated_rows_and_is_marked_teacher(
    client: TestClient,
) -> None:
    teacher = _a_teacher_with_generated_rows(client)
    before = client.get(f"/api/teachers/{teacher}/availability").json()
    assert len(before) > 1

    response = client.put(
        f"/api/teachers/{teacher}/availability",
        json={"semester": 2, "cells": [{"slot": 0, "state": "UNAVAILABLE"}]},
    )
    assert response.status_code == 200

    after = response.json()
    assert [r["slot"] for r in after] == [0]
    assert {r["source"] for r in after} == {"TEACHER"}
    assert client.get(f"/api/teachers/{teacher}/availability").json() == after


def test_a_free_week_withdraws_every_generated_row(client: TestClient) -> None:
    """The case a patch endpoint could not express."""
    teacher = _a_teacher_with_generated_rows(client)
    assert client.get(f"/api/teachers/{teacher}/availability").json()

    client.put(f"/api/teachers/{teacher}/availability", json={"semester": 2, "cells": []})
    assert client.get(f"/api/teachers/{teacher}/availability").json() == []


def test_one_teachers_declaration_leaves_the_others_untouched(client: TestClient) -> None:
    teacher = _a_teacher_with_generated_rows(client)
    others = {
        t["id"]: client.get(f"/api/teachers/{t['id']}/availability").json()
        for t in client.get("/api/instance").json()["teachers"]
        if t["id"] != teacher
    }
    client.put(f"/api/teachers/{teacher}/availability", json={"semester": 2, "cells": []})
    for other, rows in others.items():
        assert client.get(f"/api/teachers/{other}/availability").json() == rows


def test_unknown_and_duplicated_slots_are_refused(client: TestClient) -> None:
    teacher = _a_teacher_with_generated_rows(client)
    assert (
        client.put(
            f"/api/teachers/{teacher}/availability",
            json={"semester": 2, "cells": [{"slot": 999, "state": "UNAVAILABLE"}]},
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/teachers/{teacher}/availability",
            json={
                "semester": 2,
                "cells": [
                    {"slot": 1, "state": "UNAVAILABLE"},
                    {"slot": 1, "state": "PREFERRED"},
                ],
            },
        ).status_code
        == 422
    )


# ── The store, without the HTTP layer ──────────────────────────────────


def test_build_declaration_drops_available_cells_and_sorts() -> None:
    rows = build_declaration(
        teacher="T1",
        semester=2,
        cells={
            3: AvailabilityState.UNAVAILABLE,
            1: AvailabilityState.AVAILABLE,
            2: AvailabilityState.UNAVAILABLE,
        },
    )
    assert [r.slot for r in rows] == [2, 3]
    assert {r.source for r in rows} == {DeclarationSource.TEACHER}


def test_apply_declarations_does_not_mutate_the_loaded_instance(tiny_instance: Instance) -> None:
    base = dataclasses.replace(
        tiny_instance,
        availability=(
            Availability(
                teacher="T1",
                slot=0,
                state=AvailabilityState.UNAVAILABLE,
                semester=2,
                source=DeclarationSource.SYNTHETIC,
            ),
        ),
    )
    store = InMemoryAvailabilityStore()
    store.declare("T1", build_declaration("T1", 2, {4: AvailabilityState.UNAVAILABLE}))

    updated = apply_declarations(base, store)

    assert [a.slot for a in base.availability] == [0]
    assert [a.slot for a in updated.availability] == [4]
    assert effective_availability(base, store) == updated.availability
