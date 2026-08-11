"""Fixtures for the acceptance suite.

**What makes a test here different from an integration test.** An integration
test may reach for whatever seam is convenient; an acceptance test verifies a
requirement against the acceptance criterion written with it, **through the
path a user actually takes**. This project's own rule is that a requirement is
`✓` only once a user can reach it *and* it is tested end to end
(docs/requirements-traceability.md), so these drive the HTTP API rather than
calling `services/` or `analysis/` directly - even where a direct call would be
shorter and would assert the same arithmetic.

**Two engines, and the choice is per criterion, not per convenience:**

- Criteria about the ENGINE - a timetable violating no hard constraint, three
  distinct candidates, two runs agreeing - take the real CP-SAT solver at
  production settings and are marked ``solver``. Anything less would be
  verifying the fake.
- Criteria about the APPLICATION - a candidate carrying its score and
  sub-scores, contributions summing to the difference, who may read what - take
  a fake solver, because the engine is not what the criterion is about and a
  120-second solve would only make the suite too slow to run.

⚠️ Every solver-marked test fixes a seed **and** a deterministic budget
(ADR-011). A test bounded by wall clock passes on one machine and fails on
another, and the failure looks like a solver bug.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import DiagnosisResult, Placement
from optiedt.services.runs import InMemoryRunStore
from optiedt.solver.interfaces import SolverInput, SolverOutput
from optiedt.tasks.executor import RunExecutor

SOFT_CODES = frozenset({"S2", "S3", "S4", "S5", "S6", "S7", "S10"})

#: Production settings, quoted from services/portfolio.py's defaults rather
#: than invented here. C-5's resolution ties the three-candidate criterion to
#: the reference instance AT PRODUCTION SETTINGS, so a test that lowered these
#: would be verifying a different claim from the one accepted.
PRODUCTION_SEED = 42
PRODUCTION_BUDGET = 90.0


@dataclass
class FakeSolver:
    """Places every session, varying the arrangement per profile.

    Varying by profile matters: `generate_portfolio` removes duplicate
    timetables, so a fake returning one fixed assignment would exercise
    deduplication instead of the portfolio - and a criterion about several
    candidates would pass against one.

    The placements are ones the real solver could have returned, so the
    analysis layer scores them for real: every score these tests read is
    computed by `analysis/criteria.py` from actual placements, never stubbed.
    """

    offset_by_profile: dict[str, int] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def solve(self, request: SolverInput) -> SolverOutput:
        self.calls.append(request.profile.name)
        instance = request.instance
        open_slots = [s.index for s in instance.slots if s.is_open]
        offset = self.offset_by_profile.setdefault(
            request.profile.name, len(self.offset_by_profile)
        )
        placements = tuple(
            Placement(
                session=session.id,
                slot=open_slots[(index + offset) % len(open_slots)],
                room=instance.rooms[index % len(instance.rooms)].id,
            )
            for index, session in enumerate(instance.sessions)
        )
        return SolverOutput(
            placements=placements,
            cost=len(placements),
            infeasible=False,
            proven_optimal=False,
            deterministic_time_used=1.0,
            wall_clock_seconds=0.01,
        )

    def diagnose(self, request: SolverInput) -> DiagnosisResult:
        raise AssertionError("no acceptance test using the fake solver reaches stage 3")


@dataclass
class Application:
    """A signed-in client, and the executor its routes use.

    A test waits on the executor's Future rather than sleeping or polling, so
    nothing here carries a timing assumption - the run is finished when the
    Future resolves, however long the solve took.
    """

    client: TestClient
    futures: list[Future[None]]

    def launch(self, **payload: object) -> dict[str, object]:
        """`POST /runs` → 202 → wait → `GET /runs/{id}`: the whole user path."""
        body: dict[str, object] = {"seed": PRODUCTION_SEED, "deterministicBudget": 3.0}
        body.update(payload)
        created = self.client.post("/api/runs", json=body)
        assert created.status_code == 202, created.text
        run_id = created.json()["runId"]
        # Generous: a real solve at production settings takes minutes, and the
        # ceiling is a hang backstop rather than an expectation (ADR-011).
        self.futures[-1].result(timeout=900)
        response = self.client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200, response.text
        return dict(response.json())

    def regenerate(self, run_id: str, candidate_id: str, **action: object) -> dict[str, object]:
        """Accept a recommendation: 202 → wait → `GET /runs/{new_id}` (FR-23).

        Deliberately the same shape as `launch`, because that is what the
        endpoint is: accepting a recommendation launches a NEW run through the
        same engine, and a helper that made it look like an edit would hide the
        thing the requirement is about.
        """
        created = self.client.post(
            f"/api/runs/{run_id}/candidates/{candidate_id}/regenerate", json=action
        )
        assert created.status_code == 202, created.text
        new_run_id = created.json()["runId"]
        self.futures[-1].result(timeout=900)
        response = self.client.get(f"/api/runs/{new_run_id}")
        assert response.status_code == 200, response.text
        return dict(response.json())

    def read(self, run_id: str) -> dict[str, object]:
        response = self.client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200, response.text
        return dict(response.json())


@contextmanager
def wire_application(
    solver_factory,
    role: str = "PERSON_IN_CHARGE",
    instance_provider=None,
) -> Iterator[Application]:
    """The application, wired to a given solver, as a context manager.

    A context manager rather than only a fixture because the expensive suites
    need it at MODULE scope: one portfolio at production settings takes
    150 seconds, and a function-scoped fixture would re-solve for every
    assertion about the same run - five tests about one portfolio would cost
    twelve minutes and prove nothing extra. `signed_in` is function-scoped, so
    a module-scoped fixture sets the same override itself.
    """
    from optiedt.domain.entities import User
    from optiedt.domain.enums import UserRole

    for cached in (
        deps.get_settings,
        deps.get_instance,
        deps.get_availability_store,
        deps.get_calendar_store,
        deps.get_dataset_store,
        deps.get_run_store,
        deps.get_executor,
    ):
        cached.cache_clear()
    deps._parsed_dataset.clear()
    # ⚠️ `get_calendar_store` belongs in that list and its absence would be a
    # cross-test leak with teeth: the store is `lru_cache`d per process, so a
    # half-day closed by FR-9's acceptance test would still be closed for every
    # module that ran after it - and the symptom would be a *different* file
    # failing on a timetable with two fewer slots than its instance has.
    #
    # ⚠️ `get_dataset_store` (FR-1) is in the list for the same reason and with
    # sharper teeth: a dataset imported by `test_fr01` would become the base
    # instance for every module after it, so a *different* file would fail on a
    # department it never supplied. `_parsed_dataset` is the revision-keyed parse
    # of that store and is cleared with it - it is keyed by a revision the store
    # hands out, so a fresh store with no revision can never read a stale entry,
    # but clearing it keeps the two obviously in step.

    store = InMemoryRunStore()
    executor = RunExecutor(
        store=store,
        # `solve_instance` by default, not a fixed instance: it is what the
        # application itself provides, so a run here resolves declarations
        # exactly as a real one does. FR-2 meeting FR-13 is part of the path
        # under test. FR-8 and FR-12 pass their own, because their criteria are
        # about an instance that has no solution.
        instance_provider=instance_provider or deps.solve_instance,
        solver_factory=solver_factory,
    )

    futures: list[Future[None]] = []
    submit = executor.submit

    def recording_submit(run_id: str) -> Future[None]:
        future = submit(run_id)
        futures.append(future)
        return future

    executor.submit = recording_submit  # type: ignore[method-assign]

    app.dependency_overrides[deps.get_run_store] = lambda: store
    app.dependency_overrides[deps.get_executor] = lambda: executor
    # Launching a run is the person in charge's right (SRS Table 2). FR-11's
    # own acceptance test is the one that checks who may do what, with real
    # tokens; here the role is set so the criterion under test is reachable.
    app.dependency_overrides[deps.current_user] = lambda: User(
        id="acceptance-user", username="acceptance", role=UserRole(role), teacher=None
    )
    try:
        with TestClient(app) as client:
            yield Application(client=client, futures=futures)
    finally:
        executor.shutdown()
        app.dependency_overrides.clear()


def real_solver_factory():
    """The production solver, built the way `api/deps.py` builds it.

    Through `cp_sat_factory` rather than `CpSatSolver(...)` directly, so the
    configuration under test is the production one instead of a second set of
    defaults maintained here.
    """
    from optiedt.tasks.executor import cp_sat_factory

    deps.get_settings.cache_clear()
    settings = deps.get_settings()
    return cp_sat_factory(
        workers=settings.solver_workers,
        wall_clock_ceiling_seconds=settings.solver_wall_clock_ceiling_seconds,
    )


@pytest.fixture
def application() -> Iterator[Application]:
    """The application over a fake solver - for criteria about the application."""
    solver = FakeSolver()
    with wire_application(lambda: solver) as wired:
        yield wired


@pytest.fixture
def application_with_real_solver() -> Iterator[Application]:
    """The application over CP-SAT - for criteria about the engine.

    Used only by ``solver``-marked tests: a single portfolio at production
    settings takes minutes (docs/status.md measures 147-150 s), which is why
    those are excluded from `run-checks.ps1` and run by
    `scripts/run-acceptance.ps1`.
    """
    with wire_application(real_solver_factory()) as wired:
        yield wired


def solve_at_production_settings() -> dict[str, object]:
    """One run through the API, seed 42, deterministic budget 90.

    ⚠️ **The budget must be the production one, and a smaller one does not
    merely go faster - it fails.** The portfolio divides the total between the
    three profiles, and each solve carries the objective, so a total of 9 gives
    3 per profile and CP-SAT returns `UNKNOWN`: the run lands in `FAILED` and
    the engine refuses to pass it off as an answer, which is the C-13 lesson
    working. Measured while writing this suite, and consistent with
    docs/status.md's "a budget too small to solve" row.

    The 2.8-3.3 s figure recorded for a first valid timetable is a FEASIBILITY
    solve with every weight at zero. It is not a budget for this path.
    """
    with wire_application(real_solver_factory()) as application:
        run = application.launch(seed=PRODUCTION_SEED, deterministicBudget=PRODUCTION_BUDGET)
    assert run["state"] == "COMPLETED", f"state={run['state']} error={run['error']}"
    return run


def keeping_only_computer_laboratories(instance, keep: int):
    """The AREA case - an infeasibility CP-SAT CAN prove.

    Withdrawing computer laboratories leaves `Lab_Info` demand at 160 periods
    against `keep` x 28 available, which is the kind of contradiction
    `AddCumulative` reasons about directly. Measured: `INFEASIBLE` in 5.5 s,
    diagnosed `('H3',)` in 1.7 s.
    """
    import dataclasses

    from optiedt.domain.enums import RoomType

    labs = sorted((r for r in instance.rooms if r.type is RoomType.LAB_INFO), key=lambda r: r.id)
    withdrawn = {r.id for r in labs[keep:]}
    return dataclasses.replace(
        instance, rooms=tuple(r for r in instance.rooms if r.id not in withdrawn)
    )


def the_original_room_mix(instance):
    """The CONTIGUITY case - the infeasibility CP-SAT could NOT prove: C-13.

    Re-types three rooms back to the mix the instance had before the 2026-07-30
    repair: Salle 10 / Lab_Info 6 / Lab_Sciences 2. Room ids are read from the
    data rather than hardcoded, so this survives a renumbering of rooms.csv -
    the same construction as
    `tests/unit/test_preanalysis.py::test_the_original_room_mix_is_caught`.

    A room offers 11 two-period windows a week, so 6 computer laboratories
    offer 66 against 80 needed. The period bound reads a comfortable 95.2 %,
    which is exactly why it passed verification and cost three sessions.
    """
    import dataclasses

    from optiedt.domain.enums import RoomType

    labs_info = sorted(
        (r for r in instance.rooms if r.type is RoomType.LAB_INFO), key=lambda r: r.id
    )
    labs_sciences = sorted(
        (r for r in instance.rooms if r.type is RoomType.LAB_SCIENCES), key=lambda r: r.id
    )
    reverted = {r.id for r in labs_info[-2:]} | {r.id for r in labs_sciences[-1:]}
    return dataclasses.replace(
        instance,
        rooms=tuple(
            dataclasses.replace(r, type=RoomType.SALLE) if r.id in reverted else r
            for r in instance.rooms
        ),
    )


@pytest.fixture(scope="session")
def production_portfolio() -> dict[str, object]:
    """ONE portfolio at production settings, shared by every criterion that
    needs a real one.

    Session-scoped across modules on purpose. FR-3 asks whether the timetable
    violates a hard constraint, FR-13 whether three distinct candidates came
    back, FR-19 whether a repeat agrees - three different questions about the
    same kind of run, and solving separately for each would add five minutes to
    the sweep without widening a single claim.

    FR-19 still solves a SECOND run, because "repeat a run" is not a question
    one run can answer.
    """
    return solve_at_production_settings()
