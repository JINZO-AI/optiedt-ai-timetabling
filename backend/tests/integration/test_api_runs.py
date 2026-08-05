"""The run endpoints end to end, against a fake solver.

No CP-SAT here on purpose, so these stay in the fast suite: what is under test
is the lifecycle, the wire format and the layering, not the engine. The engine
has its own tests (`tests/integration/test_h1_h12.py`) and its own budget
discipline.

The fake returns placements the real solver could have returned, so the
analysis layer scores them for real - every score below is computed by
`analysis/criteria.py` from actual placements, not stubbed.
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
from optiedt.services.runs import InMemoryRunStore
from optiedt.solver.interfaces import SolverInput, SolverOutput
from optiedt.tasks.executor import RunExecutor

SOFT_CODES = {"S2", "S3", "S4", "S5", "S6", "S7", "S10"}


@dataclass
class FakeSolver:
    """Places every session, varying the arrangement per profile.

    Varying by profile matters: two identical timetables are removed as
    duplicates by `generate_portfolio`, so a fake returning one fixed
    assignment would exercise deduplication instead of the portfolio.
    """

    offset_by_profile: dict[str, int] = field(default_factory=dict)
    infeasible: bool = False
    calls: list[str] = field(default_factory=list)
    diagnosis_calls: int = 0
    conflicting_codes: tuple[str, ...] = ("H1", "H3")

    def solve(self, request: SolverInput) -> SolverOutput:
        self.calls.append(request.profile.name)
        if self.infeasible:
            return SolverOutput(
                placements=(),
                cost=0,
                infeasible=True,
                proven_optimal=False,
                deterministic_time_used=1.0,
                wall_clock_seconds=0.01,
            )
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
        """Stage 3. The real encoding is tested against CP-SAT in
        tests/unit/test_diagnosis.py; what these tests check is the LIFECYCLE
        around it, so the fake returns a fixed verdict."""
        self.diagnosis_calls += 1
        return DiagnosisResult(
            conflicting_codes=self.conflicting_codes,
            is_minimal=False,
            is_conclusive=True,
            detail="fake diagnosis",
        )


@dataclass
class Wired:
    """The client and the exact executor its routes use.

    Held together because a test waits on the executor's Future rather than
    sleeping or polling: the run is finished when the Future resolves, so these
    tests carry no timing assumption at all.
    """

    client: TestClient
    solver: FakeSolver
    futures: list[Future[None]]

    def launch(self, **payload: object) -> dict[str, object]:
        body: dict[str, object] = {"seed": 42, "deterministicBudget": 3.0}
        body.update(payload)
        created = self.client.post("/api/runs", json=body)
        assert created.status_code == 202
        run_id = created.json()["runId"]
        self.futures[-1].result(timeout=60)
        response = self.client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        return dict(response.json())


@pytest.fixture
def wired(signed_in) -> Iterator[Wired]:
    for cached in (
        deps.get_settings,
        deps.get_instance,
        deps.get_availability_store,
        deps.get_run_store,
        deps.get_executor,
    ):
        cached.cache_clear()

    solver = FakeSolver()
    instance = deps.get_instance()
    store = InMemoryRunStore()
    executor = RunExecutor(
        store=store,
        instance_provider=lambda: instance,
        solver_factory=lambda: solver,
    )

    # Record the Futures the routes create, so a test can wait deterministically.
    futures: list[Future[None]] = []
    submit = executor.submit

    def recording_submit(run_id: str) -> Future[None]:
        future = submit(run_id)
        futures.append(future)
        return future

    executor.submit = recording_submit  # type: ignore[method-assign]

    app.dependency_overrides[deps.get_run_store] = lambda: store
    app.dependency_overrides[deps.get_executor] = lambda: executor
    # Launching a run is the person in charge's right (FR-11, SRS Table 2).
    # These tests are about the LIFECYCLE; who may launch is test_rbac.py.
    signed_in("PERSON_IN_CHARGE")
    with TestClient(app) as client:
        yield Wired(client=client, solver=solver, futures=futures)
    executor.shutdown()
    app.dependency_overrides.clear()


# ── launching and polling ──────────────────────────────────────────────


def test_launching_a_run_returns_202_and_an_id_immediately(wired: Wired) -> None:
    created = wired.client.post("/api/runs", json={})
    assert created.status_code == 202
    assert set(created.json()) == {"runId"}


def test_a_run_reaches_completed_with_scored_candidates(wired: Wired) -> None:
    run = wired.launch()
    assert run["state"] == "COMPLETED"
    assert run["error"] is None

    candidates = run["candidates"]
    assert isinstance(candidates, list)
    assert candidates, "the fake places every session, so a candidate must exist"
    for candidate in candidates:
        assert 0.0 <= candidate["score"] <= 100.0
        assert len(candidate["placements"]) == 218
        assert {s["criterion"] for s in candidate["subScores"]} == SOFT_CODES


def test_candidates_come_back_in_rank_order(wired: Wired) -> None:
    """The client displays this order; it must not sort for itself."""
    run = wired.launch()
    scores = [c["score"] for c in run["candidates"]]
    assert scores == sorted(scores, reverse=True)

    listed = wired.client.get(f"/api/runs/{run['id']}/candidates").json()
    assert [c["id"] for c in listed] == [c["id"] for c in run["candidates"]]


def test_the_run_records_what_produced_it(wired: Wired) -> None:
    run = wired.launch()
    assert run["seed"] == 42
    assert run["deterministicBudget"] == 3.0
    assert run["modelVersion"]
    # One weight vector prices every candidate - the identity FR-15 rests on.
    assert set(run["weights"]) == SOFT_CODES


def test_a_run_carries_the_five_checks_it_actually_ran(wired: Wired) -> None:
    """FR-12 through the API. The report is the evidence the stage happened.

    ⚠️ An empty list means the stage did not run, and must never read as
    "verified, nothing wrong" - which is the confusion that cost three sessions
    on C-13. So the list is asserted non-empty and named, not merely present.
    """
    run = wired.launch()
    checks = run["preAnalysis"]
    assert isinstance(checks, list)
    assert [c["name"] for c in checks] == [
        "ROOM_SUITABILITY",
        "SLOT_COVERAGE",
        "TEACHER_LOAD",
        "TEACHER_FREE_SLOTS",
        "GROUP_HIERARCHY",
    ]
    assert all(c["passed"] for c in checks), checks
    assert all(c["detail"] for c in checks), "a check that says only 'passed' hides the figures"


def test_the_report_carries_the_binding_figure_not_only_a_verdict(wired: Wired) -> None:
    """The number to watch is 91 % of two-period WINDOWS, not 71 % of periods.

    The check passes either way, so if the report did not carry the figure a
    reader would have no way to see that the instance is 8 windows from
    infeasible.
    """
    coverage = next(c for c in wired.launch()["preAnalysis"] if c["name"] == "SLOT_COVERAGE")
    assert "2-period windows" in coverage["detail"]
    assert "Lab_Info" in coverage["detail"]


def test_a_run_that_found_a_timetable_carries_no_diagnosis(wired: Wired) -> None:
    """Stage 3 is entered ONLY from INFEASIBLE, never speculatively."""
    run = wired.launch()
    assert run["diagnosis"] is None
    assert wired.solver.diagnosis_calls == 0


# ── the diagnosis branch (FR-8) ────────────────────────────────────────


def test_an_infeasible_run_is_diagnosed_and_names_the_rules(wired: Wired) -> None:
    """FR-8 through the API: a report naming the rules in conflict, not a timeout."""
    wired.solver.infeasible = True
    run = wired.launch()

    assert run["state"] == "DIAGNOSED"
    assert wired.solver.diagnosis_calls == 1
    diagnosis = run["diagnosis"]
    assert diagnosis["conflictingCodes"] == ["H1", "H3"]
    assert diagnosis["isConclusive"] is True
    # ⚠️ SUFFICIENT, never minimal. The interface must not claim otherwise.
    assert diagnosis["isMinimal"] is False
    assert run["candidates"] == []


def test_an_infeasible_run_still_carries_its_pre_analysis(wired: Wired) -> None:
    """Both halves of the report, not one.

    The conflict set names rules; the pre-analysis names resources and
    quantities. On a genuinely infeasible instance the second is often the
    actionable one - C-13's conflict was capacity, which no assumption literal
    can express.
    """
    wired.solver.infeasible = True
    run = wired.launch()
    assert len(run["preAnalysis"]) == 5


def test_an_inconclusive_diagnosis_does_not_read_as_no_conflict(wired: Wired) -> None:
    """The C-13 shape: CP-SAT could not prove the infeasibility.

    An empty code list with `isConclusive` false must never be presented as
    "nothing wrong" - that is precisely the inference that cost three sessions.
    """
    wired.solver.infeasible = True
    wired.solver.conflicting_codes = ()
    run = wired.launch()

    assert run["state"] == "DIAGNOSED"
    assert run["diagnosis"]["conflictingCodes"] == []
    assert run["diagnosis"]["detail"], "an empty set must be explained in words"


def test_each_profile_is_solved_once_and_sequentially(wired: Wired) -> None:
    wired.launch()
    assert wired.solver.calls == ["balanced", "student-favouring", "teacher-favouring"]


def test_runs_are_listed_newest_first(wired: Wired) -> None:
    first = wired.launch()
    second = wired.launch()
    listed = wired.client.get("/api/runs").json()
    assert [r["id"] for r in listed][:2] == [second["id"], first["id"]]
    assert listed[0]["candidateCount"] == len(second["candidates"])


# ── comparison, dominance, recommendation ──────────────────────────────


def test_comparison_contributions_sum_to_the_score_difference(wired: Wired) -> None:
    """FR-15. The identity the whole explanation feature rests on."""
    run = wired.launch()
    candidates = run["candidates"]
    assert len(candidates) >= 2, "the fake varies placements per profile"

    a, b = candidates[0]["id"], candidates[1]["id"]
    body = wired.client.get(f"/api/runs/{run['id']}/comparison", params={"a": a, "b": b}).json()

    assert body["candidateA"] == a
    assert body["candidateB"] == b
    assert {c["criterion"] for c in body["contributions"]} == SOFT_CODES

    total = sum(c["value"] for c in body["contributions"])
    assert total == pytest.approx(body["scoreDifference"], abs=1e-9)
    assert body["scoreDifference"] == pytest.approx(
        candidates[0]["score"] - candidates[1]["score"], abs=1e-9
    )


def test_a_contribution_is_its_weight_times_the_normalised_difference(wired: Wired) -> None:
    """The figure shown IS the calculation, so the API must send its terms."""
    run = wired.launch()
    a, b = run["candidates"][0]["id"], run["candidates"][1]["id"]
    body = wired.client.get(f"/api/runs/{run['id']}/comparison", params={"a": a, "b": b}).json()
    for c in body["contributions"]:
        expected = 100.0 * c["weight"] * (c["normalisedA"] - c["normalisedB"])
        assert c["value"] == pytest.approx(expected, abs=1e-9)


def test_comparing_a_candidate_with_itself_is_refused(wired: Wired) -> None:
    run = wired.launch()
    a = run["candidates"][0]["id"]
    response = wired.client.get(f"/api/runs/{run['id']}/comparison", params={"a": a, "b": a})
    assert response.status_code == 422


def test_the_top_candidate_is_never_reported_dominated(wired: Wired) -> None:
    """C-14: provably unreachable, so the API must never claim it.

    Still true after C-14 adopted the Pareto rule on 2026-08-05, and checked
    rather than assumed: TIE_BREAK_ORDER covers all seven criteria, so even the
    score tie Pareto newly admits resolves in the dominator's favour.
    """
    run = wired.launch()
    verdicts = wired.client.get(f"/api/runs/{run['id']}/dominance").json()
    top = run["candidates"][0]["id"]
    assert all(v["dominatedBy"] is None for v in verdicts if v["candidate"] == top)


def test_the_recommendation_names_the_top_candidate_and_its_rule(wired: Wired) -> None:
    run = wired.launch()
    body = wired.client.get(f"/api/runs/{run['id']}/recommendation").json()
    assert body["candidate"] == run["candidates"][0]["id"]
    assert body["rule"]
    assert body["dominatedBy"] is None


# ── failure paths ──────────────────────────────────────────────────────


def test_unknown_run_and_candidate_are_404(wired: Wired) -> None:
    assert wired.client.get("/api/runs/nope").status_code == 404
    run = wired.launch()
    assert wired.client.get(f"/api/runs/{run['id']}/candidates/nope").status_code == 404


def test_an_infeasible_instance_walks_on_to_diagnosed(wired: Wired) -> None:
    """`INFEASIBLE` is a waypoint, not a terminal state (Phase 5 M2).

    ⚠️ Reaching `DIAGNOSED` is not the same as having a conflict to report —
    `test_an_inconclusive_diagnosis_does_not_read_as_no_conflict` covers that.
    It is also NOT a failure: `error` stays None, because an instance with no
    solution is an answer, not a fault.
    """
    wired.solver.infeasible = True
    run = wired.launch()
    assert run["state"] == "DIAGNOSED"
    assert run["candidates"] == []
    assert run["error"] is None


def test_a_solver_failure_lands_the_run_in_failed_with_a_reason(wired: Wired) -> None:
    def explode(request: SolverInput) -> SolverOutput:
        raise RuntimeError("solver exploded")

    wired.solver.solve = explode  # type: ignore[method-assign]
    run = wired.launch()
    assert run["state"] == "FAILED"
    assert run["error"] is not None
    assert "solver exploded" in run["error"]
