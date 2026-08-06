"""FR-23 — regenerate from an accepted recommendation, preserving H1-H12.

    Acceptance criterion (docs/testing-strategy.md §4):
    "New run created; new candidate satisfies H1-H12; linked to the
    recommendation."

⚠️ **This row was ⛔ out of scope from Phase 6's close until Phase 7 M2.** It
needed two things that did not exist: H10's dormant gap filled (C-19, M1) and a
layer that could assemble a `SolverInput` from a run and an override (C-20).

**Two engines, chosen per clause, as this suite's conftest requires.** "A new
run is created rather than an edit", "linked to the recommendation" and "the
override reaches the solve" are claims about the APPLICATION and take the fake
solver, so they run in `run-checks.ps1`. "The new candidate satisfies H1-H12"
is a claim about the ENGINE and takes real CP-SAT at production settings.

⚠️ **The engine half costs two production solves** - the origin run and the
regenerated one - because a regeneration is a question one run cannot answer,
exactly like FR-19's repeat.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.acceptance.conftest import (
    PRODUCTION_BUDGET,
    PRODUCTION_SEED,
    real_solver_factory,
    wire_application,
)

pytestmark = pytest.mark.acceptance


# ── the application half: a NEW RUN, never an edit ─────────────────────


def _first_candidate(run: dict[str, object]) -> dict[str, object]:
    candidates = run["candidates"]
    assert candidates, f"run produced no candidate: state={run['state']} error={run['error']}"
    return dict(candidates[0])


def test_accepting_a_recommendation_creates_a_new_run(application) -> None:
    """Invariant 3: accepting one launches a new run through the same solver
    with one input changed, **never an edit**."""
    origin = application.launch()
    candidate = _first_candidate(origin)

    regenerated = application.regenerate(
        origin["id"], candidate["id"], kind="weight_delta", criterion="S3", newWeight=0.30
    )

    assert regenerated["id"] != origin["id"]
    assert regenerated["state"] == "COMPLETED"
    assert regenerated["candidates"]


def test_the_origin_run_is_unchanged_by_the_regeneration(application) -> None:
    """Invariant 6. The whole point of a new run is that the old one keeps
    describing what it produced - a reader who compares the two must be
    comparing two records, not one record and its overwrite."""
    origin = application.launch()
    before = application.read(origin["id"])

    application.regenerate(
        origin["id"], _first_candidate(origin)["id"], kind="lock_session", session="S0001"
    )

    assert application.read(origin["id"]) == before


def test_the_new_run_is_linked_to_the_recommendation(application) -> None:
    """The criterion's third clause, and the one a trace depends on."""
    origin = application.launch()
    candidate = _first_candidate(origin)

    regenerated = application.regenerate(
        origin["id"], candidate["id"], kind="weight_delta", criterion="S3", newWeight=0.30
    )

    origin_record = regenerated["origin"]
    assert origin_record is not None
    assert origin_record["run"] == origin["id"]
    assert origin_record["candidate"] == candidate["id"]
    assert origin_record["actionKind"] == "weight_delta"
    assert "S3" in origin_record["actionDetail"]


def test_an_ordinary_run_reports_no_origin(application) -> None:
    """So that `origin: null` keeps meaning "launched from the generation
    screen" and a client can tell the two apart."""
    assert application.launch()["origin"] is None


def test_a_weight_delta_changes_the_weights_the_new_run_is_priced_under(application) -> None:
    origin = application.launch()

    regenerated = application.regenerate(
        origin["id"],
        _first_candidate(origin)["id"],
        kind="weight_delta",
        criterion="S3",
        newWeight=0.30,
    )

    assert regenerated["weights"]["S3"] == 0.30
    assert origin["weights"]["S3"] != 0.30


def test_a_lock_is_recorded_on_the_new_run_with_its_target(application) -> None:
    """`lock_session` carries a session id; the run records the SLOT AND ROOM
    it was locked to, read out of the candidate. Without the target the lock
    could not reach H10 at all - that was the dormant gap C-19 closed."""
    origin = application.launch()
    candidate = _first_candidate(origin)
    placed = next(p for p in candidate["placements"] if p["session"] == "S0001")

    regenerated = application.regenerate(
        origin["id"], candidate["id"], kind="lock_session", session="S0001"
    )

    locks = regenerated["overrides"]["lockedPlacements"]
    assert locks == [{"session": "S0001", "slot": placed["slot"], "room": placed["room"]}]


def test_an_exclusion_is_recorded_on_the_new_run(application) -> None:
    origin = application.launch()
    candidate = _first_candidate(origin)
    placed = next(p for p in candidate["placements"] if p["session"] == "S0001")

    regenerated = application.regenerate(
        origin["id"], candidate["id"], kind="exclude_slot", session="S0001", slot=placed["slot"]
    )

    assert regenerated["overrides"]["excludedSlots"] == [["S0001", placed["slot"]]]


def test_overrides_compose_across_a_chain(application) -> None:
    """C-20 clause (iv), through the API this time.

    A user who locks a session and then excludes a room must end with both.
    Discarding the first would be a lock silently vanishing.
    """
    origin = application.launch()
    first = application.regenerate(
        origin["id"], _first_candidate(origin)["id"], kind="lock_session", session="S0001"
    )
    second = application.regenerate(
        first["id"], _first_candidate(first)["id"], kind="exclude_slot", session="S0002", room="4"
    )

    assert second["overrides"]["lockedPlacements"], "the lock from the first regeneration was lost"
    assert second["overrides"]["excludedRooms"] == [["S0002", "4"]]


def test_a_fourth_action_kind_is_refused(application) -> None:
    """ADR-007: the catalogue is closed. A recommendation that cannot be
    expressed as one of the three is NOT offered, rather than approximated."""
    origin = application.launch()

    refused = application.client.post(
        f"/api/runs/{origin['id']}/candidates/{_first_candidate(origin)['id']}/regenerate",
        json={"kind": "move_session", "session": "S0001", "slot": 3},
    )

    assert refused.status_code == 422
    assert "not one of the three catalogue actions" in refused.json()["detail"]


def test_regenerating_from_an_unknown_run_is_404(application) -> None:
    assert (
        application.client.post(
            "/api/runs/nope/candidates/whatever/regenerate",
            json={"kind": "lock_session", "session": "S0001"},
        ).status_code
        == 404
    )


# ── the engine half: the new candidate satisfies H1-H12 ────────────────


@pytest.fixture(scope="module")
def regenerated_at_production_settings() -> Iterator[dict[str, dict[str, object]]]:
    """One origin run and one regeneration, both at production settings.

    Module-scoped: two real portfolios is about five minutes, and every
    assertion below is about the same pair.
    """
    with wire_application(real_solver_factory()) as application:
        origin = application.launch(seed=PRODUCTION_SEED, deterministicBudget=PRODUCTION_BUDGET)
        assert origin["state"] == "COMPLETED", f"origin failed: {origin['error']}"
        candidate = _first_candidate(origin)

        regenerated = application.regenerate(
            origin["id"], candidate["id"], kind="lock_session", session="S0001"
        )
        yield {"origin": origin, "candidate": candidate, "regenerated": regenerated}


@pytest.mark.solver
def test_the_regenerated_run_completes_against_the_real_solver(
    regenerated_at_production_settings,
) -> None:
    regenerated = regenerated_at_production_settings["regenerated"]
    assert regenerated["state"] == "COMPLETED", f"error={regenerated['error']}"
    assert regenerated["candidates"]


@pytest.mark.solver
def test_the_regenerated_candidate_places_every_session(
    regenerated_at_production_settings,
) -> None:
    """H7 in the form that matters to a user: nothing was dropped to satisfy
    the lock."""
    for candidate in regenerated_at_production_settings["regenerated"]["candidates"]:
        assert len(candidate["placements"]) == 218


@pytest.mark.solver
def test_the_locked_session_is_where_it_was_locked(
    regenerated_at_production_settings,
) -> None:
    """H10, end to end: through the API, through the store, through the
    executor, into `build_variables`, and back out in the placements."""
    original = next(
        p
        for p in regenerated_at_production_settings["candidate"]["placements"]
        if p["session"] == "S0001"
    )

    for candidate in regenerated_at_production_settings["regenerated"]["candidates"]:
        placed = next(p for p in candidate["placements"] if p["session"] == "S0001")
        assert (placed["slot"], placed["room"]) == (original["slot"], original["room"])


@pytest.mark.solver
def test_the_regenerated_candidate_violates_no_hard_constraint(
    regenerated_at_production_settings,
) -> None:
    """The criterion's second clause, re-derived from the placements rather
    than taken from CP-SAT's status - the same discipline as
    `tests/acceptance/test_fr03.py`.

    ⚠️ This is what "preserving H1-H12" in FR-23's statement means, and why a
    recommendation may only change a solver INPUT: the rules are declared
    identically in the regenerated run, so they hold for the same reason they
    held in the run the recommendation came from.
    """
    from optiedt.api import deps

    instance = deps.solve_instance()
    duration = {s.id: s.duration_periods for s in instance.sessions}
    teacher = {s.id: s.teacher for s in instance.sessions}
    open_slots = {s.index for s in instance.slots if s.is_open}
    day = {s.index: s.day_index for s in instance.slots}

    for candidate in regenerated_at_production_settings["regenerated"]["candidates"]:
        occupied_by_teacher: dict[tuple[str, int], str] = {}
        occupied_by_room: dict[tuple[str, int], str] = {}

        for placement in candidate["placements"]:
            session = placement["session"]
            span = range(placement["slot"], placement["slot"] + duration[session])

            # H9: every period occupied is an open slot.
            assert all(period in open_slots for period in span), f"{session} touches a closed slot"
            # H8: a multi-period session stays inside one day.
            assert len({day[period] for period in span}) == 1, f"{session} crosses a day boundary"

            for period in span:
                # H1: one teacher, one place at a time.
                key = (teacher[session], period)
                assert key not in occupied_by_teacher, (
                    f"teacher {teacher[session]} is in two places at period {period}: "
                    f"{occupied_by_teacher[key]} and {session}"
                )
                occupied_by_teacher[key] = session

                # H3: one room, one session at a time.
                room_key = (placement["room"], period)
                assert room_key not in occupied_by_room, (
                    f"room {placement['room']} holds two sessions at period {period}: "
                    f"{occupied_by_room[room_key]} and {session}"
                )
                occupied_by_room[room_key] = session
