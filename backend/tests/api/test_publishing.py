"""Editing, approval, publication, dated views and exceptions over HTTP."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from optiedt.models import Activity, Solution, Term
from optiedt.problem.snapshot import session_id
from tests import factories

API = "/api/v1"

pytestmark = pytest.mark.solver


def _as(client: TestClient, db: Session, role: str, department_id: uuid.UUID | None = None) -> None:
    username = f"{role.replace('_', '.')}.{uuid.uuid4().hex[:6]}"
    factories.user(db, username, [(role, department_id)])
    factories.login(client, username)


def _setup(db: Session) -> tuple[Term, Solution, dict[str, str]]:
    _, term = factories.populated_term(db)
    draft = factories.solved_draft(db, term.id)
    ids = {}
    for activity in db.scalars(select(Activity).where(Activity.term_id == term.id)):
        key = "lecture" if activity.sessions_per_week == 2 else "tutorial"
        ids[key] = str(session_id(activity.id, 1))
    return term, draft, ids


def _solution(client: TestClient, solution_id: object) -> dict[str, Any]:
    body: dict[str, Any] = client.get(f"{API}/solutions/{solution_id}").json()
    return body


def test_editing_endpoints(client: TestClient, db: Session) -> None:
    _, draft, ids = _setup(db)
    _as(client, db, "scheduling_officer")
    timetable = client.get(f"{API}/solutions/{draft.id}/timetable").json()
    tutorial = next(s for s in timetable["sessions"] if s["id"] == ids["tutorial"])
    lecture = next(s for s in timetable["sessions"] if s["id"] == ids["lecture"])
    clash = {
        "session_id": ids["lecture"],
        "day": tutorial["day"],
        "period": tutorial["period"],
        "room_id": lecture["room_id"],
    }
    version = _solution(client, draft.id)["version"]

    dry = client.post(
        f"{API}/solutions/{draft.id}/moves",
        json={"version": version, "moves": [clash], "dry_run": True},
    ).json()
    assert dry["applied"] is False
    assert dry["preview"]["valid"] is False

    refused = client.post(
        f"{API}/solutions/{draft.id}/moves", json={"version": version, "moves": [clash]}
    )
    assert refused.status_code == 409
    assert refused.json()["code"] == "move_invalid"
    assert refused.json()["details"]["preview"]["introduced"]

    suggestions = client.get(
        f"{API}/solutions/{draft.id}/suggestions", params={"session_id": ids["lecture"]}
    ).json()
    target = next(o for o in suggestions["valid"] if not o["is_current"])
    moved = client.post(
        f"{API}/solutions/{draft.id}/moves",
        json={
            "version": version,
            "moves": [
                {
                    "session_id": ids["lecture"],
                    **{k: target[k] for k in ("day", "period", "room_id")},
                }
            ],
            "reason": "Better slot",
        },
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["solution"]["version"] > version

    version = moved.json()["solution"]["version"]
    locked = client.put(
        f"{API}/solutions/{draft.id}/locks",
        json={"version": version, "session_ids": [ids["tutorial"]], "locked": True},
    )
    assert locked.status_code == 200
    changes = client.get(f"{API}/solutions/{draft.id}/changes").json()
    assert [c["kind"] for c in changes] == ["move", "lock"]
    assert changes[0]["reason"] == "Better slot"

    copy = client.post(f"{API}/solutions/{draft.id}/duplicate", json={"name": "Variant"})
    assert copy.status_code == 201
    assert copy.json()["origin"] == "copy"


def test_publication_flow_and_dated_views(client: TestClient, db: Session) -> None:
    term, draft, ids = _setup(db)
    _as(client, db, "system_admin")
    version = _solution(client, draft.id)["version"]
    submitted = client.post(f"{API}/solutions/{draft.id}/submit", json={"version": version})
    assert submitted.json()["status"] == "pending_approval"
    approved = client.post(
        f"{API}/solutions/{draft.id}/approve",
        json={"version": submitted.json()["version"], "note": "OK"},
    )
    assert approved.json()["status"] == "approved"
    body = {"version": approved.json()["version"], "note": "First version"}
    published = client.post(
        f"{API}/solutions/{draft.id}/publish", json=body, headers={"Idempotency-Key": "publish-001"}
    )
    assert published.status_code == 201, published.text
    replay = client.post(
        f"{API}/solutions/{draft.id}/publish", json=body, headers={"Idempotency-Key": "publish-001"}
    )
    assert replay.json()["id"] == published.json()["id"]
    publication = published.json()
    assert publication["version_no"] == 1

    listed = client.get(f"{API}/terms/{term.id}/publications").json()
    assert [p["version_no"] for p in listed] == [1]
    weekly = client.get(f"{API}/publications/{publication['id']}/timetable").json()
    assert len(weekly["sessions"]) == 3

    start = term.start_date
    end = start + timedelta(days=6)
    week = client.get(
        f"{API}/publications/{publication['id']}/occurrences",
        params={"from": start.isoformat(), "to": end.isoformat()},
    ).json()
    assert len(week) == 3
    lecture = next(o for o in week if o["session_id"] == ids["lecture"])
    cancelled = client.post(
        f"{API}/publications/{publication['id']}/exceptions",
        json={
            "session_id": ids["lecture"],
            "occurrence_date": lecture["date"],
            "kind": "cancelled",
            "notice": "Lecture cancelled today",
        },
    )
    assert cancelled.status_code == 201, cancelled.text
    week = client.get(
        f"{API}/publications/{publication['id']}/occurrences",
        params={"from": start.isoformat(), "to": end.isoformat()},
    ).json()
    status = next(o for o in week if o["session_id"] == ids["lecture"])
    assert status["status"] == "cancelled"
    assert status["notice"] == "Lecture cancelled today"
    revoked = client.delete(f"{API}/exceptions/{cancelled.json()['id']}")
    assert revoked.json()["revoked_at"] is not None

    tutorial = next(o for o in week if o["session_id"] == ids["tutorial"])
    plan = client.post(
        f"{API}/publications/{publication['id']}/disruptions",
        json={
            "resource_kind": "room",
            "resource_id": tutorial["room_id"],
            "start": tutorial["date"],
            "end": tutorial["date"],
        },
    ).json()
    assert [entry["action"] for entry in plan] == ["relocated"]
    applied = client.post(
        f"{API}/publications/{publication['id']}/disruptions/apply",
        json={
            "changes": [
                {
                    "session_id": plan[0]["session_id"],
                    "occurrence_date": plan[0]["date"],
                    "kind": "relocated",
                    "new_room_id": plan[0]["new_room_id"],
                }
            ],
            "reason": "Maintenance",
        },
    )
    assert applied.status_code == 201, applied.text

    backwards = client.get(
        f"{API}/publications/{publication['id']}/occurrences",
        params={"from": end.isoformat(), "to": start.isoformat()},
    )
    assert backwards.status_code == 422

    _as(client, db, "viewer")
    assert client.get(f"{API}/publications/{publication['id']}/timetable").status_code == 200
    assert (
        client.post(
            f"{API}/publications/{publication['id']}/exceptions",
            json={
                "session_id": ids["tutorial"],
                "occurrence_date": (
                    date.fromisoformat(tutorial["date"]) + timedelta(days=7)
                ).isoformat(),
                "kind": "cancelled",
            },
        ).status_code
        == 403
    )
    assert client.post(f"{API}/solutions/{draft.id}/submit", json={"version": 1}).status_code == 403
