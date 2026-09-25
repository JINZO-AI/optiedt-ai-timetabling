from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests import factories

API = "/api/v1"


def _officer(client: TestClient, db: Session, department_id=None) -> None:  # type: ignore[no-untyped-def]
    factories.user(db, "officer", [("scheduling_officer", department_id)])
    factories.login(client, "officer")


def _grid(client: TestClient, term_id: object) -> dict[str, object]:
    response = client.get(f"{API}/terms/{term_id}/time-grid")
    assert response.status_code == 200
    result: dict[str, object] = response.json()
    return result


def _group(client: TestClient, term_id: object, **body: object) -> dict[str, object]:
    response = client.post(f"{API}/terms/{term_id}/groups", json=body)
    assert response.status_code == 201, response.text
    result: dict[str, object] = response.json()
    return result


def test_term_creation_seeds_objective_profiles(client: TestClient, db: Session) -> None:
    factories.user(db, "registrar", [("institution_admin", None)])
    factories.login(client, "registrar")
    response = client.post(
        f"{API}/terms",
        json={
            "code": "2026-S2",
            "name": "Spring semester",
            "academic_year": "2026-2027",
            "start_date": "2027-02-01",
            "end_date": "2027-06-15",
            "weekdays": [0, 1, 2, 3, 4, 5],
            "periods": [
                {"label": "P1", "start_time": "08:30", "end_time": "10:00"},
                {"label": "P2", "start_time": "10:10", "end_time": "11:40", "joins_next": True},
            ],
        },
    )
    assert response.status_code == 201, response.text
    term = response.json()
    grid = _grid(client, term["id"])
    assert [p["joins_next"] for p in grid["periods"]] == [True, False]  # type: ignore[union-attr, index]
    profiles = client.get(f"{API}/terms/{term['id']}/objective-profiles").json()
    assert {p["code"] for p in profiles} == {
        "balanced",
        "student_centred",
        "instructor_centred",
        "room_efficient",
    }


def test_overlapping_periods_are_rejected(client: TestClient, db: Session) -> None:
    term = factories.term(db)
    factories.user(db, "registrar", [("institution_admin", None)])
    factories.login(client, "registrar")
    grid = _grid(client, term.id)
    response = client.put(
        f"{API}/terms/{term.id}/time-grid",
        json={
            "version": grid["term_version"],
            "weekdays": [0, 1, 2],
            "periods": [
                {"label": "P1", "start_time": "08:00", "end_time": "10:00"},
                {"label": "P2", "start_time": "09:30", "end_time": "11:00"},
            ],
        },
    )
    assert response.status_code == 422


def test_time_grid_update_keeps_period_identity_and_prunes_cells(
    client: TestClient, db: Session
) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    factories.user(db, "registrar", [("system_admin", None)])
    factories.login(client, "registrar")
    grid = _grid(client, term.id)
    periods = grid["periods"]
    teacher = inst.instructors["T100"]
    put = client.put(
        f"{API}/terms/{term.id}/availability/instructor/{teacher.id}",
        json={
            "cells": [
                {"weekday": 4, "period_id": periods[0]["id"], "state": "unavailable"},  # type: ignore[index]
                {"weekday": 0, "period_id": periods[3]["id"], "state": "undesirable"},  # type: ignore[index]
            ]
        },
    )
    assert put.status_code == 200, put.text

    kept = [
        {
            "id": p["id"],
            "label": p["label"],
            "start_time": p["start_time"],
            "end_time": p["end_time"],
            "joins_next": p["joins_next"],
        }
        for p in periods[:3]  # type: ignore[index]
    ]
    response = client.put(
        f"{API}/terms/{term.id}/time-grid",
        json={
            "version": grid["term_version"],
            "weekdays": [0, 1, 2, 3],
            "periods": kept,
            "slots": [
                {"weekday": 2, "period_index": 2, "is_closed": True, "closed_reason": "Sports"},
                {"weekday": 3, "period_index": 0, "penalty": 2},
            ],
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert [p["id"] for p in updated["periods"]] == [p["id"] for p in kept]
    assert {(x["weekday"], x["is_closed"], x["penalty"]) for x in updated["slots"]} == {
        (2, True, 0),
        (3, False, 2),
    }
    cells = client.get(f"{API}/terms/{term.id}/availability/instructor/{teacher.id}").json()
    assert cells["cells"] == []  # Friday removed, P4 removed


def test_removing_a_period_with_fixed_placements_is_refused(
    client: TestClient, db: Session
) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    grid = _grid(client, term.id)
    periods = grid["periods"]
    group = _group(client, term.id, code="L2-CS", name="L2 Computer Science", size=80)
    activity = client.post(
        f"{API}/terms/{term.id}/activities",
        json={
            "course_id": str(inst.courses["CS201"].id),
            "activity_type_id": str(inst.lecture.id),  # type: ignore[union-attr]
            "group_ids": [group["id"]],
            "instructor_ids": [str(inst.instructors["T100"].id)],
            "fixed": [{"occurrence": 1, "weekday": 0, "period_id": periods[3]["id"]}],  # type: ignore[index]
        },
    )
    assert activity.status_code == 201, activity.text
    factories.user(db, "registrar", [("system_admin", None)])
    factories.login(client, "registrar")
    response = client.put(
        f"{API}/terms/{term.id}/time-grid",
        json={
            "version": grid["term_version"],
            "weekdays": [0, 1, 2, 3, 4],
            "periods": [
                {
                    "id": p["id"],
                    "label": p["label"],
                    "start_time": p["start_time"],
                    "end_time": p["end_time"],
                }
                for p in periods[:3]  # type: ignore[index]
            ],
        },
    )
    assert response.status_code == 409
    assert "CS201" in response.json()["detail"]


def test_group_tree_with_partitions(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    cohort = _group(
        client,
        term.id,
        code="L2-CS",
        name="L2 CS",
        size=90,
        programme_id=str(inst.programme.id),  # type: ignore[union-attr]
    )
    for code in ("G1", "G2", "G3"):
        _group(
            client,
            term.id,
            code=f"L2-CS-{code}",
            name=code,
            size=30,
            parent_id=cohort["id"],
            partition_key="tutorial",
        )
    _group(
        client,
        term.id,
        code="L2-CS-EN",
        name="English",
        size=50,
        parent_id=cohort["id"],
        partition_key="language",
    )
    listed = client.get(f"{API}/terms/{term.id}/groups").json()
    assert len(listed["items"]) == 5
    assert listed["warnings"] == [
        "Partition 'language' of L2-CS: subgroups total 50 students, the group has 90."
    ]
    cycle = client.patch(
        f"{API}/terms/{term.id}/groups/{cohort['id']}",
        json={"version": cohort["version"], "parent_id": listed["items"][1]["id"]},
    )
    assert cycle.status_code == 422
    in_use = client.delete(f"{API}/terms/{term.id}/groups/{cohort['id']}")
    assert in_use.status_code == 409


def test_activity_validation_names_each_problem(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db, weekdays=(0, 1))
    other_term = factories.term(db, code="2025-S2")
    _officer(client, db)
    foreign = _group(client, other_term.id, code="X", name="Other term", size=10)
    periods = _grid(client, term.id)["periods"]
    response = client.post(
        f"{API}/terms/{term.id}/activities",
        json={
            "course_id": str(inst.courses["CS201"].id),
            "activity_type_id": str(inst.tutorial.id),  # type: ignore[union-attr]
            "group_ids": [foreign["id"]],
            "sessions_per_week": 3,
            "delivery_mode": "online",
            "room_type_id": str(inst.classroom.id),
            "fixed": [{"occurrence": 4, "weekday": 5, "period_id": periods[0]["id"]}],  # type: ignore[index]
        },
    )
    assert response.status_code == 422
    fields = {e["field"] for e in response.json()["errors"]}
    assert {
        "group_ids",
        "sessions_per_week",
        "delivery_mode",
        "fixed.0.occurrence",
        "fixed.0.weekday",
    } <= fields


def test_activity_links_update_and_version(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    group = _group(client, term.id, code="L2-CS", name="L2 CS", size=35)
    created = client.post(
        f"{API}/terms/{term.id}/activities",
        json={
            "course_id": str(inst.courses["CS202"].id),
            "activity_type_id": str(inst.tutorial.id),  # type: ignore[union-attr]
            "group_ids": [group["id"]],
            "instructor_ids": [str(inst.instructors["T100"].id)],
            "duration": 2,
            "sessions_per_week": 2,
            "rooms": [{"room_id": str(inst.rooms["A-101"].id), "kind": "preferred"}],
        },
    )
    assert created.status_code == 201, created.text
    activity = created.json()
    updated = client.patch(
        f"{API}/terms/{term.id}/activities/{activity['id']}",
        json={
            "version": activity["version"],
            "instructor_ids": [
                str(inst.instructors["T100"].id),
                str(inst.instructors["T101"].id),
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    assert len(updated.json()["instructor_ids"]) == 2
    assert updated.json()["version"] == activity["version"] + 1
    assert updated.json()["rooms"] == activity["rooms"]
    by_teacher = client.get(
        f"{API}/terms/{term.id}/activities",
        params={"instructor_id": str(inst.instructors["T101"].id)},
    ).json()
    assert [a["id"] for a in by_teacher] == [activity["id"]]


def test_scoped_officer_cannot_touch_other_departments(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    admin = factories.admin_principal(db)
    _ = admin
    factories.user(db, "cs.officer", [("scheduling_officer", inst.cs.id)])
    factories.login(client, "cs.officer")
    group = client.post(
        f"{API}/terms/{term.id}/groups",
        json={"code": "L1", "name": "L1", "size": 10, "programme_id": str(inst.programme.id)},  # type: ignore[union-attr]
    )
    assert group.status_code == 201, group.text
    denied = client.post(
        f"{API}/terms/{term.id}/activities",
        json={
            "course_id": str(inst.courses["MA201"].id),
            "activity_type_id": str(inst.lecture.id),  # type: ignore[union-attr]
            "group_ids": [group.json()["id"]],
        },
    )
    assert denied.status_code == 403


def test_instructor_declares_own_availability_only_while_open(
    client: TestClient, db: Session
) -> None:
    inst = factories.institution(db)
    teacher = inst.instructors["T100"]
    open_term = factories.term(db, open_until=date.today() + timedelta(days=7))
    closed_term = factories.term(db, code="2025-S2", open_until=date.today() - timedelta(days=1))
    factories.user(db, "leila", [("instructor", None)], instructor_id=teacher.id)
    factories.login(client, "leila")
    period = _grid(client, open_term.id)["periods"][0]["id"]  # type: ignore[index]
    cells = {"cells": [{"weekday": 1, "period_id": period, "state": "preferred"}]}
    ok = client.put(f"{API}/terms/{open_term.id}/availability/instructor/{teacher.id}", json=cells)
    assert ok.status_code == 200, ok.text
    assert ok.json()["source"] == "self"

    closed_period = _grid(client, closed_term.id)["periods"][0]["id"]  # type: ignore[index]
    closed = client.put(
        f"{API}/terms/{closed_term.id}/availability/instructor/{teacher.id}",
        json={"cells": [{"weekday": 1, "period_id": closed_period, "state": "preferred"}]},
    )
    assert closed.status_code == 403
    other = client.put(
        f"{API}/terms/{open_term.id}/availability/instructor/{inst.instructors['T101'].id}",
        json=cells,
    )
    assert other.status_code == 403


def test_room_availability_accepts_only_unavailable(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    period = _grid(client, term.id)["periods"][0]["id"]  # type: ignore[index]
    response = client.put(
        f"{API}/terms/{term.id}/availability/room/{inst.rooms['A-101'].id}",
        json={"cells": [{"weekday": 0, "period_id": period, "state": "preferred"}]},
    )
    assert response.status_code == 422


def test_rule_validation_and_references(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    term = factories.term(db)
    _officer(client, db)
    bad_params = client.post(
        f"{API}/terms/{term.id}/rules",
        json={
            "rule_type": "max_periods_per_day",
            "params": {"limit": 0},
            "scope": {"all_groups": True},
        },
    )
    assert bad_params.status_code == 422
    assert bad_params.json()["errors"][0]["field"] == "params"
    unknown = client.post(
        f"{API}/terms/{term.id}/rules",
        json={
            "rule_type": "max_days_per_week",
            "params": {"limit": 3},
            "scope": {"instructor_ids": ["00000000-0000-0000-0000-000000000009"]},
        },
    )
    assert unknown.status_code == 422
    ok = client.post(
        f"{API}/terms/{term.id}/rules",
        json={
            "rule_type": "max_days_per_week",
            "name": "Dr Mansouri teaches at most 3 days",
            "enforcement": "soft",
            "tier": 1,
            "weight": 5,
            "params": {"limit": 3},
            "scope": {"instructor_ids": [str(inst.instructors["T100"].id)]},
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["scope"]["instructor_ids"] == [str(inst.instructors["T100"].id)]


def test_profile_rejects_unknown_objective(client: TestClient, db: Session) -> None:
    term = factories.term(db)
    _officer(client, db)
    response = client.post(
        f"{API}/terms/{term.id}/objective-profiles",
        json={
            "code": "custom",
            "name": "Custom",
            "objectives": {"happiness": {"tier": 1, "weight": 1}},
        },
    )
    assert response.status_code == 422


def test_copy_term_structure(client: TestClient, db: Session) -> None:
    inst = factories.institution(db)
    source = factories.term(db, code="2025-S1")
    target = factories.term(db, code="2026-S1")
    _officer(client, db)
    cohort = _group(client, source.id, code="L2", name="L2", size=60)
    sub = _group(client, source.id, code="L2-G1", name="G1", size=30, parent_id=cohort["id"])
    period = _grid(client, source.id)["periods"][1]["id"]  # type: ignore[index]
    activity = client.post(
        f"{API}/terms/{source.id}/activities",
        json={
            "course_id": str(inst.courses["CS201"].id),
            "activity_type_id": str(inst.tutorial.id),  # type: ignore[union-attr]
            "group_ids": [sub["id"]],
            "instructor_ids": [str(inst.instructors["T101"].id)],
            "fixed": [{"occurrence": 1, "weekday": 2, "period_id": period}],
        },
    ).json()
    lecture = client.post(
        f"{API}/terms/{source.id}/activities",
        json={
            "course_id": str(inst.courses["CS201"].id),
            "activity_type_id": str(inst.lecture.id),  # type: ignore[union-attr]
            "group_ids": [cohort["id"]],
            "instructor_ids": [str(inst.instructors["T100"].id)],
        },
    ).json()
    duplicate = client.post(
        f"{API}/terms/{source.id}/rules",
        json={
            "rule_type": "precedence",
            "params": {},
            "scope": {"activity_ids": [activity["id"], activity["id"]]},
        },
    )
    assert duplicate.status_code == 422
    rule = client.post(
        f"{API}/terms/{source.id}/rules",
        json={
            "rule_type": "precedence",
            "params": {},
            "scope": {"first_activity_id": lecture["id"], "second_activity_id": activity["id"]},
        },
    )
    assert rule.status_code == 201, rule.text
    factories.user(db, "admin", [("system_admin", None)])
    factories.login(client, "admin")
    response = client.post(
        f"{API}/terms/{target.id}/copy-from",
        json={"source_term_id": str(source.id), "include": ["groups", "activities", "rules"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["copied"] == {"groups": 2, "activities": 2, "rules": 1}
    copied = [a for a in client.get(f"{API}/terms/{target.id}/activities").json() if a["fixed"]]
    target_period = _grid(client, target.id)["periods"][1]["id"]  # type: ignore[index]
    assert copied[0]["fixed"][0]["period_id"] == target_period
    assert copied[0]["group_ids"] != [sub["id"]]
