"""The student's surface — SRS Table 2.

    The right, transcribed in docs/domain-model.md's "Roles and rights" table,
    which SRS Table 2 governs (C-8):
    "Student — read the timetable of their group."

    The Cahier des Charges adds printing:
    "students to consult and print the timetable of their group."

⚠️ **This file quotes SRS Table 2, and Table 2 is a table of RIGHTS rather than
an acceptance test.** It is therefore a weaker source than the criteria in
`docs/testing-strategy.md` §4, which the supervisor wrote as tests (Table 35)
or as input/processing/output rows (§3.2), and it must not be presented as one
of them. The student surface has no requirement code of its own: what it
belongs to is FR-11 (*restrict access by role*), whose own criterion — "connect
with a teacher account, access limited to own data" — is verified in
`test_fr11.py`. Read this file as the same sentence applied to the other role
Table 2 scopes.

**Two things it establishes, and the second is the reason it exists:**

1. A student reaches the published timetable of their own group.
2. **A student reaches nothing else.** Phase 9's audit recorded that
   `GET /runs/{id}` accepted any authenticated caller. That was harmless while
   every role worked on timetables; a student is the first role for which it is
   not, because a run carries every group's DRAFT weeks.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import Candidate, Placement, SubScore, User
from optiedt.domain.enums import UserRole
from optiedt.services.publications import InMemoryPublicationStore, new_publication
from optiedt.services.runs import InMemoryRunStore, RunRequest, new_run_record
from tests.acceptance.conftest import FakeSolver, wire_application

pytestmark = pytest.mark.acceptance

#: A laboratory subgroup of the reference instance, and its chain. Group 3 is
#: INFO-L1-G1.1, whose parent is the tutorial group 2 and whose grandparent is
#: the promotion 1 - so its week is drawn from all three, a CM being addressed
#: to the promotion.
SUBGROUP = "3"
TUTORIAL_GROUP = "2"
PROMOTION = "1"


@pytest.fixture
def instance():
    deps.get_instance.cache_clear()
    return deps.get_instance()


def _session_of(instance, group: str) -> str:
    """One session addressed to exactly this group."""
    return next(s.id for s in instance.sessions if s.group == group)


@pytest.fixture
def published(instance) -> Iterator[TestClient]:
    """A published timetable covering the subgroup, its parents and a stranger.

    ⚠️ **Assembled directly rather than solved.** The criterion is about who
    sees what, not about the engine: a 150-second portfolio would make this
    suite too slow to run and would not widen a single claim. The placements
    are real sessions of the real instance, so the filtering under test is the
    filtering a user gets.
    """
    runs = InMemoryRunStore()
    publications = InMemoryPublicationStore()

    record = new_run_record(
        "run-1", RunRequest(seed=42, deterministic_budget=90.0), weights={"S2": 1.0}
    )
    stranger_group = next(
        g.id for g in instance.groups if g.id not in {SUBGROUP, TUTORIAL_GROUP, PROMOTION}
    )
    placements = tuple(
        Placement(session=_session_of(instance, group), slot=slot, room="R01")
        for slot, group in enumerate((PROMOTION, TUTORIAL_GROUP, SUBGROUP, stranger_group))
    )
    candidate = Candidate(
        id="cand-1",
        run=record.run.id,
        profile_name="balanced",
        cost=0,
        score=80.0,
        placements=placements,
        sub_scores=(SubScore(criterion="S2", raw_value=1.0, normalised=1.0),),
    )
    runs.create(record)
    runs.save(dataclasses.replace(record, candidates=(candidate,)))
    publications.publish(new_publication(candidate.id, record.run.id, "responsable"))

    solver = FakeSolver()
    with wire_application(lambda: solver, role="STUDENT") as wired:
        app.dependency_overrides[deps.get_run_store] = lambda: runs
        app.dependency_overrides[deps.get_publication_store] = lambda: publications
        app.dependency_overrides[deps.current_user] = lambda: User(
            id="etudiant", username="etudiant", role=UserRole.STUDENT, group=SUBGROUP
        )
        yield wired.client
    deps.get_calendar_store.cache_clear()


def test_a_student_reads_the_published_timetable_of_their_group(
    published: TestClient, instance
) -> None:
    """**The right itself.** The week includes the group's ancestors' sessions.

    ⚠️ A CM is addressed to the promotion, so a subgroup shown only the
    sessions carrying its own id would display a week with holes its students
    do not have - the same relation H12 uses in the solver and
    `features/timetable/model.ts` applies for the other views.
    """
    response = published.get("/api/me/timetable")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["group"] == SUBGROUP
    sessions = {p["session"] for p in body["placements"]}
    assert sessions == {
        _session_of(instance, PROMOTION),
        _session_of(instance, TUTORIAL_GROUP),
        _session_of(instance, SUBGROUP),
    }


def test_another_groups_sessions_never_reach_the_payload(published: TestClient, instance) -> None:
    """⚠️ **Filtered on the SERVER, which is the whole point of the endpoint.**

    A payload carrying all 218 placements with the browser hiding the rest
    would be granting the student every group's week and calling the difference
    presentation. Authorisation a client performs is not authorisation, and
    this is the assertion that would fail if the filter moved.
    """
    stranger_group = next(
        g.id for g in instance.groups if g.id not in {SUBGROUP, TUTORIAL_GROUP, PROMOTION}
    )

    body = published.get("/api/me/timetable").json()

    assert _session_of(instance, stranger_group) not in {p["session"] for p in body["placements"]}


def test_the_group_comes_from_the_account_and_not_from_the_request(
    published: TestClient,
) -> None:
    """The line Phase 5 drew for a teacher, drawn again for a student.

    There is no group in the path, so there is nothing for a request to assert.
    The endpoint reads `/api/me/timetable` and the account decides the rest.
    """
    assert published.get("/api/me/timetable").json()["group"] == SUBGROUP
    # No route admits a group of the caller's choosing.
    assert published.get(f"/api/me/timetable?group={PROMOTION}").json()["group"] == SUBGROUP


def test_the_trace_of_what_was_published_travels_with_it(published: TestClient) -> None:
    """A student is told which timetable this is and when it was adopted.

    ⚠️ It carries the publication, not the run's candidates: a run holds three
    ranked DRAFTS, and telling students to follow one the department never
    adopted would be worse than showing them nothing.
    """
    body = published.get("/api/me/timetable").json()

    assert body["publishedBy"] == "responsable"
    assert body["publishedAt"] is not None
    assert body["candidate"] == "cand-1"


def test_nothing_published_reads_as_an_absence_rather_than_an_error() -> None:
    """⚠️ 200 with an empty week, not 404.

    "Nothing has been published yet" and "what you asked for does not exist"
    read completely differently to a student, and only the first is true. The
    same judgement `acceptance/test_fr25` makes for a report that must say
    plainly when nothing was published.
    """
    solver = FakeSolver()
    with wire_application(lambda: solver, role="STUDENT") as wired:
        app.dependency_overrides[deps.current_user] = lambda: User(
            id="etudiant", username="etudiant", role=UserRole.STUDENT, group=SUBGROUP
        )
        response = wired.client.get("/api/me/timetable")
    deps.get_calendar_store.cache_clear()

    assert response.status_code == 200
    body = response.json()
    assert body["placements"] == []
    assert body["publishedAt"] is None
    assert body["group"] == SUBGROUP


def test_a_student_account_with_no_group_is_refused_rather_than_defaulted() -> None:
    """An account that cannot say whose timetable it owns has no business being
    shown one, and a default would hand it somebody else's — the same rule
    `docs/domain-model.md` states for a teacher account with no teacher."""
    solver = FakeSolver()
    with wire_application(lambda: solver, role="STUDENT") as wired:
        app.dependency_overrides[deps.current_user] = lambda: User(
            id="orphelin", username="orphelin", role=UserRole.STUDENT
        )
        response = wired.client.get("/api/me/timetable")
    deps.get_calendar_store.cache_clear()

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/runs",
        "/api/publications",
        "/api/teachers/T001/availability",
        "/api/calendar",
        "/api/accounts",
    ],
)
def test_a_student_reaches_no_other_timetable_surface(published: TestClient, path: str) -> None:
    """**The second half of the right, and the reason this file exists.**

    ⚠️ Every one of these answered 200 to a student before Phase 11 except the
    last two, which did not exist. `GET /runs` carries every group's drafts;
    `/publications` carries every published week with its trace; the
    availability grid is another person's declared week — Table 2 gives the
    student none of them.
    """
    assert published.get(path).status_code == 403, path


def test_a_student_still_reads_the_instance(published: TestClient) -> None:
    """⚠️ Deliberately NOT restricted, and the reason is in `routers/instance`.

    The slot grid, the rooms and the group hierarchy are what any screen needs
    to render anything at all, and none of it is personal data — the 425
    students are not even loaded (`domain/instance.py`). Restricting it would
    break the student's own timetable rather than protect anybody.
    """
    assert published.get("/api/instance").status_code == 200
