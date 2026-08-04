"""The wire format, pinned.

Two properties are guarded here, both of which are cheap to break by tidying:

1. **Enum values on the wire are the French literals of the instance CSVs.**
   `frontend/src/types/domain.ts` shipped with an English `RoomType`
   (`LECTURE_THEATRE`, `CLASSROOM`, ...) that matched nothing the API can send,
   so a room filter written against it would have matched zero rows while
   looking correct. Anglicising an enum "for consistency" is a one-line change
   that breaks every screen quietly; this test makes it loud.

2. **Field names are camelCase**, which is what `domain.ts` declares.

Neither needs a solver or a database, so both run in the fast suite.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from optiedt.api.deps import get_availability_store, get_instance, get_settings
from optiedt.api.main import app
from optiedt.domain.enums import GroupLevel, RoomType, SessionType, TeacherRank


@pytest.fixture
def client(signed_in) -> Iterator[TestClient]:
    # Caches are per-process; clear them so a test never inherits another
    # test's declarations through the in-memory store.
    get_settings.cache_clear()
    get_instance.cache_clear()
    get_availability_store.cache_clear()
    # Every endpoint needs a token since FR-11 (Phase 5 M4). These tests are
    # about the WIRE FORMAT, so they sign in rather than acquire a concern.
    signed_in("PERSON_IN_CHARGE")
    yield TestClient(app)


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_room_types_on_the_wire_are_the_french_literals(client: TestClient) -> None:
    payload = client.get("/api/instance").json()
    seen = {r["type"] for r in payload["rooms"]}
    assert seen <= {"Amphi", "Salle", "Lab_Info", "Lab_Sciences"}
    # The repaired instance carries all four types (C-13), so this is an
    # equality rather than a subset in practice - state it, so a room type
    # silently disappearing from the instance also fails here.
    assert seen == {"Amphi", "Salle", "Lab_Info", "Lab_Sciences"}
    assert seen == {t.value for t in RoomType}


def test_session_and_group_vocabulary_is_not_translated(client: TestClient) -> None:
    payload = client.get("/api/instance").json()
    assert {s["type"] for s in payload["sessions"]} == {"CM", "TD", "TP"}
    assert {s["requiredRoomType"] for s in payload["sessions"]} <= {t.value for t in RoomType}
    assert {g["level"] for g in payload["groups"]} == {"PROMO", "TD", "TP"}
    assert {t.value for t in SessionType} == {"CM", "TD", "TP"}
    assert {g.value for g in GroupLevel} == {"PROMO", "TD", "TP"}


def test_teacher_ranks_keep_their_unaccented_french_spelling(client: TestClient) -> None:
    payload = client.get("/api/instance").json()
    assert {t["rank"] for t in payload["teachers"]} == {
        "Professeur",
        "Maitre de Conferences",
        "Maitre Assistant",
        "Assistant",
    }
    assert {r.value for r in TeacherRank} == {t["rank"] for t in payload["teachers"]}


def test_field_names_are_camel_case(client: TestClient) -> None:
    payload = client.get("/api/instance").json()
    assert set(payload["slots"][0]) == {
        "index",
        "dayIndex",
        "periodIndex",
        "startHour",
        "endHour",
        "isOpen",
    }
    assert "durationPeriods" in payload["sessions"][0]
    assert "requiredRoomType" in payload["sessions"][0]
    assert "maxHoursPerWeek" in payload["teachers"][0]
    assert "parentGroup" in payload["groups"][0]
    assert "defaultWeight" in payload["constraints"][0]


def test_hours_are_rendered_for_display_not_as_iso_times(client: TestClient) -> None:
    slot = client.get("/api/instance").json()["slots"][0]
    assert slot["startHour"] == "08:30"
    assert slot["endHour"] == "10:00"


def test_the_instance_matches_its_documented_shape(client: TestClient) -> None:
    """Guards the payload, not the instance - verify-instance.ps1 does that.

    Included because a mapping bug that drops a collection is invisible in a
    schema test and obvious here.
    """
    payload = client.get("/api/instance").json()
    assert len(payload["sessions"]) == 218
    assert len(payload["groups"]) == 51
    assert len(payload["teachers"]) == 44
    assert len(payload["rooms"]) == 20
    assert len(payload["slots"]) == 30
    assert sum(1 for s in payload["slots"] if s["isOpen"]) == 28
    assert len(payload["constraints"]) == 19
