"""Scenarios, runs and solutions over HTTP."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from optiedt.config import Settings
from optiedt.models import Term
from optiedt.worker.main import Worker
from tests import factories

API = "/api/v1"


def _term(db: Session) -> tuple[factories.Institution, Term]:
    return factories.populated_term(db)


def _as(client: TestClient, db: Session, role: str, department_id: uuid.UUID | None = None) -> None:
    username = f"{role.replace('_', '.')}.{uuid.uuid4().hex[:6]}"
    factories.user(db, username, [(role, department_id)])
    factories.login(client, username)


def _scenario(client: TestClient, term_id: uuid.UUID, **body: Any) -> dict[str, Any]:
    response = client.post(
        f"{API}/terms/{term_id}/scenarios",
        json={"name": "First draft", "profile_codes": ["balanced", "student_centred"], **body},
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def test_scenarios_are_validated(client: TestClient, db: Session) -> None:
    _, term = _term(db)
    _as(client, db, "scheduling_officer")
    scenario = _scenario(client, term.id, time_limit_seconds=30)
    assert scenario["solver_mode"] == "fastest"
    assert scenario["time_limit_seconds"] == 30

    bad = client.post(
        f"{API}/terms/{term.id}/scenarios",
        json={"name": "Bad", "profile_codes": ["nonexistent"]},
    )
    assert bad.status_code == 422
    assert bad.json()["errors"][0]["field"] == "profile_codes"

    scoped = client.post(
        f"{API}/terms/{term.id}/scenarios",
        json={
            "name": "Scoped",
            "profile_codes": ["balanced"],
            "scope_department_ids": [str(uuid.uuid4())],
        },
    )
    assert scoped.status_code == 422
    fields = {e["field"] for e in scoped.json()["errors"]}
    assert fields == {"scope_department_ids", "base_solution_id"}

    patched = client.patch(
        f"{API}/scenarios/{scenario['id']}",
        json={"version": scenario["version"], "seed": 42},
    )
    assert patched.status_code == 200
    stale = client.patch(
        f"{API}/scenarios/{scenario['id']}", json={"version": scenario["version"], "seed": 7}
    )
    assert stale.status_code == 409

    archived = client.post(f"{API}/scenarios/{scenario['id']}/archive")
    assert archived.json()["archived_at"] is not None
    listed = client.get(f"{API}/terms/{term.id}/scenarios").json()
    assert listed == []


def test_department_officers_may_only_schedule_their_departments(
    client: TestClient, db: Session
) -> None:
    inst, term = _term(db)
    _as(client, db, "scheduling_officer", inst.cs.id)
    whole = client.post(
        f"{API}/terms/{term.id}/scenarios", json={"name": "All", "profile_codes": ["balanced"]}
    )
    assert whole.status_code == 403
    assert "institution-wide" in whole.json()["detail"]

    _as(client, db, "viewer")
    assert client.get(f"{API}/terms/{term.id}/scenarios").status_code == 403


def test_run_requests_are_idempotent_and_one_at_a_time(client: TestClient, db: Session) -> None:
    _, term = _term(db)
    _as(client, db, "scheduling_officer")
    scenario = _scenario(client, term.id)
    url = f"{API}/scenarios/{scenario['id']}/runs"

    first = client.post(url, headers={"Idempotency-Key": "request-0001"})
    assert first.status_code == 202, first.text
    run = first.json()
    assert run["status"] == "queued"
    assert run["settings"]["profiles"] == ["balanced", "student_centred"]
    assert run["settings"]["mode"] == "fastest"

    replay = client.post(url, headers={"Idempotency-Key": "request-0001"})
    assert replay.status_code == 202
    assert replay.json()["id"] == run["id"]

    another = client.post(url, headers={"Idempotency-Key": "request-0002"})
    assert another.status_code == 409
    assert another.json()["code"] == "run_active"

    other_scenario = _scenario(client, term.id, name="Second")
    reused = client.post(
        f"{API}/scenarios/{other_scenario['id']}/runs", headers={"Idempotency-Key": "request-0001"}
    )
    assert reused.status_code == 409
    assert reused.json()["code"] == "idempotency_key_reused"

    cancelled = client.post(f"{API}/runs/{run['id']}/cancel")
    assert cancelled.json()["status"] == "cancelled"
    assert client.post(f"{API}/runs/{run['id']}/cancel").status_code == 409
    events = client.get(f"{API}/runs/{run['id']}/events").json()
    assert [e["kind"] for e in events] == ["queued", "cancelled"]


@pytest.mark.solver
def test_from_request_to_compared_timetables(
    client: TestClient,
    db: Session,
    worker_sessions: Callable[[], Session],
    worker_settings: Settings,
) -> None:
    _, term = _term(db)
    _as(client, db, "scheduling_officer")
    scenario = _scenario(client, term.id, time_limit_seconds=5)
    run = client.post(f"{API}/scenarios/{scenario['id']}/runs").json()
    assert Worker(worker_settings, worker_sessions, worker_id="api-worker").run_once()

    done = client.get(f"{API}/runs/{run['id']}").json()
    assert done["status"] == "succeeded", done["error_message"]
    assert done["progress"]["phase"]
    assert client.get(f"{API}/runs/{run['id']}/log").text

    listed = client.get(f"{API}/terms/{term.id}/solutions", params={"run_id": run["id"]}).json()
    assert listed["total"] == 2
    first, second = listed["items"]
    assert first["is_complete"]
    assert first["hard_violation_count"] == 0
    assert len(first["tiers"]) == 6

    timetable = client.get(f"{API}/solutions/{first['id']}/timetable").json()
    assert len(timetable["sessions"]) == 3
    assert timetable["unscheduled"] == []
    assert all(s["day"] is not None for s in timetable["sessions"])
    lecture = next(s for s in timetable["sessions"] if s["type"] == "LEC")
    assert timetable["resources"]["rooms"][lecture["room_id"]]["code"] == "A-AMPHI"

    evaluation = client.get(f"{API}/solutions/{first['id']}/evaluation").json()
    assert evaluation["violations"] == []
    assert evaluation["solver_agrees"] is True

    compared = client.get(
        f"{API}/solutions/compare",
        params={"ids": [first["id"], second["id"]], "profile": "balanced"},
    ).json()
    assert set(compared["ranking"]) == {first["id"], second["id"]}
    assert compared["differences"][0]["id"] == second["id"]

    explanation = client.get(f"{API}/solutions/{first['id']}/unscheduled/{lecture['id']}").json()
    assert explanation["windows"] == 20
    assert explanation["rooms"] == 1

    _as(client, db, "department_head")
    assert client.get(f"{API}/solutions/{first['id']}/timetable").status_code == 200
    assert client.get(f"{API}/runs/{run['id']}/log").status_code == 403
