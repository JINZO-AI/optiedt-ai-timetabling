"""FR-19's acceptance criterion, end to end.

    Every published timetable traces back to its run, seed and weights.

⚠️ **The criterion is about what a reader can establish, not about what is
stored.** A publication that recorded only a candidate id would satisfy any
test asking "is it saved?" and fail the criterion for anyone holding the
answer. So the assertions below are on what `GET /publications` actually
returns, and they check that the trace matches the RUN — not that two copies of
the seed agree with each other.

These run against the fake solver, in the fast suite: what is under test is the
trace, not the engine.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import Future
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from optiedt.api import deps
from optiedt.api.main import app
from optiedt.domain.entities import DiagnosisResult, Placement
from optiedt.services.publications import InMemoryPublicationStore
from optiedt.services.runs import InMemoryRunStore
from optiedt.solver.interfaces import SolverInput, SolverOutput
from optiedt.tasks.executor import RunExecutor


@dataclass
class FakeSolver:
    offset_by_profile: dict[str, int] = field(default_factory=dict)

    def solve(self, request: SolverInput) -> SolverOutput:
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

    def diagnose(self, request: SolverInput) -> DiagnosisResult:  # pragma: no cover
        raise AssertionError("a feasible run must not enter the diagnosis")


@dataclass
class Wired:
    client: TestClient
    futures: list[Future[None]]

    def completed_run(self) -> dict:
        created = self.client.post("/api/runs", json={"seed": 7, "deterministicBudget": 3.0})
        assert created.status_code == 202
        run_id = created.json()["runId"]
        self.futures[-1].result(timeout=60)
        run = self.client.get(f"/api/runs/{run_id}").json()
        assert run["state"] == "COMPLETED"
        return dict(run)


@pytest.fixture
def wired(signed_in) -> Iterator[Wired]:
    for cached in (
        deps.get_settings,
        deps.get_instance,
        deps.get_availability_store,
        deps.get_run_store,
        deps.get_publication_store,
        deps.get_executor,
    ):
        cached.cache_clear()

    instance = deps.get_instance()
    store = InMemoryRunStore()
    # ⚠️ Built ONCE. `lambda: InMemoryPublicationStore()` would hand a fresh,
    # empty store to every request, so publishing and listing would not share
    # one - and the criterion would fail for a reason that is entirely the
    # test's own.
    publications = InMemoryPublicationStore()
    executor = RunExecutor(
        store=store,
        instance_provider=lambda: instance,
        solver_factory=FakeSolver,
    )
    futures: list[Future[None]] = []
    submit = executor.submit

    def recording_submit(run_id: str) -> Future[None]:
        future = submit(run_id)
        futures.append(future)
        return future

    executor.submit = recording_submit  # type: ignore[method-assign]

    app.dependency_overrides[deps.get_run_store] = lambda: store
    app.dependency_overrides[deps.get_publication_store] = lambda: publications
    app.dependency_overrides[deps.get_executor] = lambda: executor
    signed_in("PERSON_IN_CHARGE")
    with TestClient(app) as client:
        yield Wired(client=client, futures=futures)
    executor.shutdown()
    app.dependency_overrides.clear()


# ── the acceptance criterion ───────────────────────────────────────────


def test_a_published_timetable_traces_back_to_its_run_seed_and_weights(
    wired: Wired,
) -> None:
    """**The acceptance criterion, checked on what a reader receives.**

    Every field is compared against the RUN, so a publication that stored its
    own copy of the seed could not pass by agreeing with itself.
    """
    run = wired.completed_run()
    candidate = run["candidates"][0]

    published = wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish")
    assert published.status_code == 201
    body = published.json()

    assert body["run"] == run["id"]
    assert body["seed"] == run["seed"] == 7
    assert body["weights"] == run["weights"]
    assert body["modelVersion"] == run["modelVersion"]
    assert body["deterministicBudget"] == run["deterministicBudget"]
    assert body["candidate"]["id"] == candidate["id"]


def test_the_trace_is_complete_when_read_back_not_only_when_written(
    wired: Wired,
) -> None:
    """⚠️ Publishing returns the trace; so must LISTING.

    A criterion satisfied only in the response to the act that created the
    record is not satisfied at all — nobody reads a timetable by re-publishing
    it.
    """
    run = wired.completed_run()
    candidate = run["candidates"][0]
    wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish")

    listed = wired.client.get("/api/publications").json()
    assert len(listed) == 1
    assert listed[0]["seed"] == run["seed"]
    assert listed[0]["weights"] == run["weights"]
    assert listed[0]["modelVersion"] == run["modelVersion"]
    assert listed[0]["candidate"]["placements"]


def test_publication_records_who_published_and_when(wired: Wired) -> None:
    run = wired.completed_run()
    candidate = run["candidates"][0]
    body = wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish").json()

    assert body["publishedBy"] == "test"
    assert body["publishedAt"]


def test_the_seed_reported_is_the_runs_own_not_a_default(wired: Wired) -> None:
    """The run was launched with seed 7, not the configured default of 42.

    If the trace were assembled from settings rather than from the run, this is
    the assertion that would catch it — and every other field would still look
    right.
    """
    run = wired.completed_run()
    body = wired.client.post(
        f"/api/runs/{run['id']}/candidates/{run['candidates'][0]['id']}/publish"
    ).json()
    assert body["seed"] == 7


def test_publishing_twice_replaces_rather_than_duplicates(wired: Wired) -> None:
    """The department publishes A timetable; a history of "published again" is
    not something any requirement asks for or any screen shows."""
    run = wired.completed_run()
    candidate = run["candidates"][0]
    for _ in range(2):
        wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish")

    assert len(wired.client.get("/api/publications").json()) == 1


def test_publishing_a_second_candidate_adds_a_second_publication(wired: Wired) -> None:
    run = wired.completed_run()
    assert len(run["candidates"]) >= 2
    for candidate in run["candidates"][:2]:
        wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish")

    assert len(wired.client.get("/api/publications").json()) == 2


# ── failure paths and rights ───────────────────────────────────────────


def test_an_unknown_run_or_candidate_is_404(wired: Wired) -> None:
    run = wired.completed_run()
    assert wired.client.post("/api/runs/nope/candidates/x/publish").status_code == 404
    assert wired.client.post(f"/api/runs/{run['id']}/candidates/nope/publish").status_code == 404


def test_only_the_person_in_charge_may_publish(wired: Wired, signed_in) -> None:
    """SRS Table 2. Publication is the one action here with a consequence
    outside the application: it is what teachers are told to follow."""
    run = wired.completed_run()
    candidate = run["candidates"][0]

    for role in ("TEACHER", "ADMINISTRATOR", "STUDENT"):
        signed_in(role, "T001" if role == "TEACHER" else None)
        response = wired.client.post(f"/api/runs/{run['id']}/candidates/{candidate['id']}/publish")
        assert response.status_code == 403, role
        assert wired.client.get("/api/publications").status_code == 403, role
