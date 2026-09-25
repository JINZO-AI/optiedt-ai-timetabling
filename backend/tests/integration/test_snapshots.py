from __future__ import annotations

from datetime import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from optiedt.problem.model import build_problem
from optiedt.problem.snapshot import content_hash, session_id
from optiedt.services.snapshots import compile_snapshot, load_snapshot, store_snapshot
from tests import factories


def test_snapshot_resolves_references_to_indices(db: Session) -> None:
    inst, term = factories.populated_term(db)
    snapshot = compile_snapshot(db, term.id)
    assert [d.weekday for d in snapshot.days] == [0, 1, 2, 3, 4]
    assert [p.label for p in snapshot.periods] == ["P1", "P2", "P3", "P4"]
    teacher = next(i for i in snapshot.instructors if i.code == "T100")
    assert teacher.unavailable == [(0, 0)]
    assert teacher.undesirable == [(1, 3)]

    lecture = next(a for a in snapshot.activities if a.sessions_per_week == 2)
    assert lecture.min_capacity == 60  # defaults to the cohort size
    assert lecture.room_type_id == str(inst.lecture_hall.id)  # from the activity type
    assert lecture.different_days is True
    assert [s.id for s in snapshot.sessions if s.activity_id == lecture.id] == [
        str(session_id(lecture.id, 1)),
        str(session_id(lecture.id, 2)),
    ]

    rule = snapshot.rules[0]
    assert rule.params == {"min_free": 1, "periods": [1, 2]}
    assert set(rule.instructor_ids) == {
        str(inst.instructors["T100"].id),
        str(inst.instructors["T101"].id),
    }

    problem = build_problem(snapshot)
    assert len(problem.sessions) == 3
    assert problem.slot_times[problem.slot(0, 0)] == (time(8, 30), time(10, 0))


def test_identical_data_gives_identical_hash_and_one_stored_snapshot(db: Session) -> None:
    _, term = factories.populated_term(db)
    first = compile_snapshot(db, term.id)
    second = compile_snapshot(db, term.id)
    assert content_hash(first.model_dump(mode="json")) == content_hash(
        second.model_dump(mode="json")
    )
    stored_a = store_snapshot(db, term.id, first)
    stored_b = store_snapshot(db, term.id, second)
    assert stored_a.id == stored_b.id
    assert load_snapshot(stored_a) == first


def test_changing_data_changes_hash(db: Session) -> None:
    inst, term = factories.populated_term(db)
    before = content_hash(compile_snapshot(db, term.id).model_dump(mode="json"))
    inst.rooms["A-101"].capacity = 45
    db.flush()
    after = content_hash(compile_snapshot(db, term.id).model_dump(mode="json"))
    assert before != after


def test_validation_endpoint_reports_issues(client: TestClient, db: Session) -> None:
    inst, term = factories.populated_term(db)
    inst.rooms["A-AMPHI"].is_active = False  # the only lecture hall
    db.flush()
    factories.user(db, "officer", [("scheduling_officer", None)])
    factories.login(client, "officer")
    response = client.get(f"/api/v1/terms/{term.id}/validation")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["counts"]["sessions"] == 3
    assert body["errors"] >= 1
    codes = [i["code"] for i in body["feasibility_issues"]]
    assert "no_compatible_room" in codes
    message = next(i for i in body["feasibility_issues"] if i["code"] == "no_compatible_room")
    assert "60 seats" in message["message"]
