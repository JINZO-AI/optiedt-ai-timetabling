"""FR-20 — the timetable of an examination session.

    Criterion (SRS §3.2, Table 19. FR-20. Examination session), quoted verbatim:
      Input       Examinations, students, rooms, period of the session and
                  supervisors
      Processing  Construction of the model of section 6.8 then solving
      Output      One slot and one or more rooms assigned to each examination

    And PPM's completion criterion for the phase, quoted verbatim:
      "The timetable of an examination session is produced under the
       constraints X1 to X4"

⚠️ **The constraints are re-derived from the placements, never taken from
CP-SAT's status.** That is the same discipline `test_fr03` applies to H1–H12
and `test_h1_h12` before it: a solver reporting OPTIMAL tells you the model it
was given was satisfied, not that the model was the right one. Every one of
X1–X4 below is recomputed here from the examination timetable a user obtains
through the API, against the roster and the room list.

⚠️ **SX1 is recomputed independently too.** ADR-011 records that
`CpSolver.objective_value` can sit above the objective at the solution actually
returned, so the penalty the API reports is checked against a recomputation
from the placements rather than trusted.

⚠️ **Nothing here is taken from ITC-2007.** Track 1 has never been opened
(ADR-008) and a benchmark's constraints are not this product's requirements.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import dataclass, replace

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import User
from optiedt.domain.enums import UserRole
from optiedt.domain.examination import ExamPlacement, ExamTimetable
from optiedt.instance.loader import load_instance, resolve_instance_path
from optiedt.services.examinations import ExaminationService, InMemoryExamRunStore

pytestmark = pytest.mark.acceptance
"""⚠️ Required, and its absence is silent. `run-acceptance.ps1` selects by this
MARKER, not by the directory, so a file without it sits in tests/acceptance/,
passes under run-checks.ps1, and is absent from the one report that answers
"is FR-20 verified against its criterion?". Phase 12 lost 34 tests exactly that
way and found it by comparing two counts."""


@dataclass
class ExamApplication:
    client: TestClient
    futures: list[Future[None]]

    def generate(self, **params: object) -> dict:
        """`POST /examinations` → 202 → wait → `GET`: the whole user path."""
        created = self.client.post("/api/examinations", params=params)
        assert created.status_code == 202, created.text
        run_id = created.json()["id"]
        self.futures[-1].result(timeout=900)
        response = self.client.get(f"/api/examinations/{run_id}")
        assert response.status_code == 200, response.text
        return dict(response.json())


@contextmanager
def wire_examinations(
    solver_factory, role: str = "PERSON_IN_CHARGE", instance_provider=None
) -> Iterator[ExamApplication]:
    for cached in (
        deps.get_settings,
        deps.get_instance,
        deps.get_availability_store,
        deps.get_calendar_store,
        deps.get_dataset_store,
        deps.get_examination_service,
    ):
        cached.cache_clear()
    deps._parsed_dataset.clear()

    service = ExaminationService(
        store=InMemoryExamRunStore(),
        instance_provider=instance_provider or deps.solve_instance,
        solver_factory=solver_factory,
    )
    futures: list[Future[None]] = []
    start = service.start

    def recording_start(**kwargs):
        record, future = start(**kwargs)
        futures.append(future)
        return record, future

    service.start = recording_start  # type: ignore[method-assign]

    app.dependency_overrides[deps.get_examination_service] = lambda: service
    app.dependency_overrides[deps.current_user] = lambda: User(
        id="acceptance-user", username="acceptance", role=UserRole(role), teacher=None
    )
    try:
        with TestClient(app) as client:
            yield ExamApplication(client=client, futures=futures)
    finally:
        service.shutdown()
        app.dependency_overrides.clear()


def _real_exam_solver_factory():
    from optiedt.services.examinations import exam_solver_factory

    deps.get_settings.cache_clear()
    settings = deps.get_settings()
    return exam_solver_factory(
        workers=settings.solver_workers,
        wall_clock_ceiling_seconds=settings.solver_wall_clock_ceiling_seconds,
    )


@dataclass
class FakeExamSolver:
    """Places every examination in its own slot, one room each.

    Enough to exercise the application — lifecycle, authorisation, rendering —
    without a half-minute solve. Every criterion about the ENGINE takes the
    real solver below and is marked `solver`.
    """

    def solve(self, session, rooms) -> ExamTimetable:
        return ExamTimetable(
            placements=tuple(
                ExamPlacement(
                    examination=exam.id,
                    slot=session.slots[index % len(session.slots)].index,
                    rooms=(rooms[0].id,),
                )
                for index, exam in enumerate(session.examinations)
            ),
            spread_penalty=0,
            proven_optimal=True,
            wall_clock_seconds=0.01,
        )


# ── the engine: X1–X4 re-derived from a real solve ─────────────────────


@pytest.fixture(scope="module")
def real_examination_timetable() -> Iterator[dict]:
    """One real examination solve at production settings, shared by the
    engine tests — the same economy `solve_at_production_settings` applies to
    the weekly suite."""
    with wire_examinations(_real_exam_solver_factory()) as wired:
        yield wired.generate(seed=42, deterministic_budget=30.0)


@pytest.mark.solver
def test_every_examination_is_placed_once_in_one_slot_and_one_or_more_rooms(
    real_examination_timetable: dict,
) -> None:
    """FR-20's OUTPUT, exactly as Table 19 words it."""
    run = real_examination_timetable
    assert run["state"] == "COMPLETED", run.get("error")

    placements = run["placements"]
    assert len(placements) == run["examinationCount"]
    assert run["examinationCount"] == 32, "the reference instance has 32 courses"

    placed_once = [p["examination"] for p in placements]
    assert len(set(placed_once)) == len(placed_once), "an examination placed twice"

    for placement in placements:
        assert isinstance(placement["slot"], int)
        assert len(placement["rooms"]) >= 1, (
            "Table 19 promises one slot and ONE OR MORE rooms; "
            f"{placement['examination']} received none"
        )


@pytest.mark.solver
def test_x1_no_student_sits_two_examinations_in_one_slot(
    real_examination_timetable: dict,
) -> None:
    """X1, re-derived per INDIVIDUAL student from the roster.

    Not per promotion: SRS §6.8 states the rule per student because *"two
    students of the same group may present different optional courses"*. On
    this instance the two readings coincide, and the test still computes the
    one the specification states.
    """
    instance = load_instance(resolve_instance_path("../data/instance"))
    by_promotion: dict[str, list[str]] = {}
    for student in instance.students:
        by_promotion.setdefault(student.promotion, []).append(student.id)
    assert instance.students, "the roster is what X1 is about"

    slot_of: dict[str, int] = {}
    promotion_of: dict[str, str] = {}
    for placement in real_examination_timetable["placements"]:
        slot_of[placement["examination"]] = placement["slot"]
        promotion_of[placement["examination"]] = placement["promotion"]

    for student in instance.students:
        their_slots = [
            slot_of[exam]
            for exam, promotion in promotion_of.items()
            if promotion == student.promotion
        ]
        assert len(their_slots) == len(set(their_slots)), (
            f"student {student.id} sits two examinations in one slot"
        )


@pytest.mark.solver
def test_x2_the_assigned_rooms_cover_the_candidates(
    real_examination_timetable: dict,
) -> None:
    """X2 — *"capacity of the rooms covering the number of candidates"*,
    checked as the SUM SRS §6.8 specifies rather than against a single room."""
    instance = load_instance(resolve_instance_path("../data/instance"))
    capacity = {room.id: room.capacity for room in instance.rooms}

    for placement in real_examination_timetable["placements"]:
        assigned = sum(capacity[r] for r in placement["rooms"])
        assert assigned >= placement["candidateCount"], (
            f"{placement['examination']}: {assigned} seats for "
            f"{placement['candidateCount']} candidates"
        )
        # The figure the API reports must be the same arithmetic, not a second
        # answer free to drift from it.
        assert placement["assignedCapacity"] == assigned


@pytest.mark.solver
def test_x3_every_examination_falls_inside_the_period_and_outside_the_holidays(
    real_examination_timetable: dict,
) -> None:
    """X3, re-derived against the calendar rather than trusted to the domain
    of the variable that enforces it."""
    from datetime import date, timedelta

    instance = load_instance(resolve_instance_path("../data/instance"))
    start = date.fromisoformat(instance.calendar_config["exam_period_start"])
    days = int(instance.calendar_config["exam_period_days"])
    last = start + timedelta(days=days - 1)
    blocked = {h.date for h in instance.holidays if h.blocking}

    seen = set()
    for placement in real_examination_timetable["placements"]:
        day = date.fromisoformat(placement["day"])
        seen.add(day)
        assert start <= day <= last, f"{day} is outside the examination period"
        assert day not in blocked, f"{day} is a blocking holiday"
        assert day.weekday() < 6, f"{day} is a Sunday"

    assert blocked & {start + timedelta(days=offset) for offset in range(days)}, (
        "the period must span a holiday, or X3's exclusion is never exercised"
    )
    assert seen, "no examination was placed"


@pytest.mark.solver
def test_x4_no_supervisor_is_in_two_examinations_at_once(
    real_examination_timetable: dict,
) -> None:
    """X4, re-derived from the supervisor each examination reports."""
    by_supervisor: dict[str, list[int]] = {}
    for placement in real_examination_timetable["placements"]:
        by_supervisor.setdefault(placement["supervisor"], []).append(placement["slot"])

    shared = [s for s, slots in by_supervisor.items() if len(slots) > 1]
    assert shared, (
        "no supervisor holds two examinations, so this test could not fail; "
        "the reference instance has 18 supervisors over 32 examinations"
    )
    for supervisor, slots in by_supervisor.items():
        assert len(slots) == len(set(slots)), (
            f"supervisor {supervisor} is in two examinations in one slot"
        )


@pytest.mark.solver
def test_a_room_never_hosts_two_examinations_in_one_slot(
    real_examination_timetable: dict,
) -> None:
    """The examination counterpart of H3. Implied by X2 being satisfiable at
    all, and checked because a multi-room model makes double-booking easy to
    introduce and invisible in the totals."""
    occupied: dict[tuple[str, int], str] = {}
    for placement in real_examination_timetable["placements"]:
        for room in placement["rooms"]:
            key = (room, placement["slot"])
            assert key not in occupied, (
                f"room {room} hosts {occupied[key]} and "
                f"{placement['examination']} in slot {placement['slot']}"
            )
            occupied[key] = placement["examination"]


@pytest.mark.solver
def test_sx1_the_reported_spread_penalty_is_recomputable_from_the_placements(
    real_examination_timetable: dict,
) -> None:
    """SX1, recomputed here rather than read from the solver's objective —
    ADR-011's reason: the reported objective can sit above the objective at
    the solution actually returned."""
    run = real_examination_timetable
    counts: dict[tuple[str, str], int] = {}
    for placement in run["placements"]:
        counts[(placement["promotion"], placement["day"])] = (
            counts.get((placement["promotion"], placement["day"]), 0) + 1
        )
    recomputed = sum(max(0, n - 1) for n in counts.values())
    assert run["spreadPenalty"] == recomputed


# ── the application: lifecycle, authorisation, refusals ────────────────


def test_the_run_answers_202_and_is_polled_to_completion() -> None:
    """ADR-005's shape: no HTTP request is held open for a solve."""
    with wire_examinations(lambda: FakeExamSolver()) as wired:
        created = wired.client.post("/api/examinations")
        assert created.status_code == 202
        assert created.json()["state"] == "PENDING"
        assert created.json()["placements"] == []

        wired.futures[-1].result(timeout=60)
        run = wired.client.get(f"/api/examinations/{created.json()['id']}").json()
        assert run["state"] == "COMPLETED"
        assert len(run["placements"]) == 32


def test_an_unknown_examination_run_is_404() -> None:
    with wire_examinations(lambda: FakeExamSolver()) as wired:
        assert wired.client.get("/api/examinations/nope").status_code == 404


@pytest.mark.parametrize("role", ["ADMINISTRATOR", "TEACHER", "STUDENT"])
def test_only_the_person_in_charge_may_generate_an_examination_session(role: str) -> None:
    """SRS Table 2 — generating a timetable is the person in charge's right,
    weekly or examination. C-8 settled that Table 2 wins over the flow prose."""
    with wire_examinations(lambda: FakeExamSolver(), role=role) as wired:
        assert wired.client.post("/api/examinations").status_code == 403
        assert wired.client.get("/api/examinations").status_code == 403


def test_a_dataset_without_a_roster_is_refused_with_the_reason() -> None:
    """The honest failure, and the one a department will actually meet.

    `students.csv` is not among the eleven files FR-1 admits, so a supplied
    dataset carries no roster — and X1 and X2 are both about students. The run
    must say so in words the person in charge can act on, not fail as
    "generation failed" or, worse, solve against zero candidates.
    """
    stripped = replace(load_instance(resolve_instance_path("../data/instance")), students=())
    with wire_examinations(lambda: FakeExamSolver(), instance_provider=lambda: stripped) as wired:
        run = wired.generate()

    assert run["state"] == "FAILED"
    assert run["placements"] == []
    assert "no students" in (run["error"] or "")
    assert "students.csv" in (run["error"] or ""), (
        "the message must name the file, or the reader cannot act on it"
    )


@pytest.mark.solver
def test_an_examination_larger_than_every_single_room_is_split_across_rooms() -> None:
    """R-6, exercised rather than assumed.

    ⚠️ `solver`-marked because it drives real CP-SAT: this is a criterion about
    the ENGINE, and an unmarked real solve would put half a minute into
    `run-checks.ps1`, which the fast/solver split exists to prevent.

    ⚠️ On the reference instance the largest examination is 120 candidates and
    Amphi A seats 250, so every examination happens to fit in one room and the
    multi-room capability is never *exercised* by the reference data. This test
    removes the two amphitheatres, leaving no room above 45 seats against a
    120-candidate examination, so X2 can only be satisfied by a SUM — which is
    what SRS §6.8 says room assignment becomes.
    """
    from optiedt.examination.derive import derive_examination_session
    from optiedt.examination.solver import ExamSolver

    instance = load_instance(resolve_instance_path("../data/instance"))
    small_rooms = tuple(r for r in instance.rooms if r.capacity <= 45)
    assert max(r.capacity for r in small_rooms) < 120

    session = derive_examination_session(instance, deterministic_budget=10.0)
    biggest = max(e.candidate_count for e in session.examinations)
    assert biggest > max(r.capacity for r in small_rooms)

    timetable = ExamSolver(workers=4).solve(session, small_rooms)
    assert not timetable.infeasible

    capacity = {r.id: r.capacity for r in small_rooms}
    multi = [p for p in timetable.placements if len(p.rooms) > 1]
    assert multi, "no examination used several rooms, so R-6 was not exercised"
    for placement in timetable.placements:
        exam = next(e for e in session.examinations if e.id == placement.examination)
        assert sum(capacity[r] for r in placement.rooms) >= exam.candidate_count
