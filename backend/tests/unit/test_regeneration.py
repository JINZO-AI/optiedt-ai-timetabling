"""The rules `services/regeneration.py` exists to keep (FR-23, C-20).

Each test names one of the three, or one of the refusals. They are unit tests
against records rather than through the API, because what is under test is the
ASSEMBLY - `tests/acceptance/test_fr23.py` is what proves a user can reach it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from optiedt.domain.entities import (
    Candidate,
    Placement,
    Run,
    RunOverrides,
    SubScore,
)
from optiedt.domain.enums import RunState
from optiedt.recommendations.catalogue import ExcludeSlot, LockSession, WeightDelta
from optiedt.services.regeneration import (
    RegenerationError,
    action_from_wire,
    regenerate,
)
from optiedt.services.runs import RunRecord

WEIGHTS = {"S2": 0.15, "S3": 0.15, "S4": 0.10, "S5": 0.20, "S6": 0.10, "S7": 0.20, "S10": 0.0}


def _candidate(candidate_id: str = "c1") -> Candidate:
    return Candidate(
        id=candidate_id,
        run="r1",
        profile_name="balanced",
        cost=100,
        score=80.0,
        placements=(
            Placement(session="S0001", slot=7, room="2"),
            Placement(session="S0002", slot=3, room="4"),
        ),
        sub_scores=(SubScore(criterion="S2", raw_value=5.0, normalised=0.9),),
    )


def _record(state: RunState = RunState.COMPLETED, **kwargs) -> RunRecord:
    return RunRecord(
        run=Run(
            id="r1",
            created_at=datetime(2026, 8, 6, tzinfo=UTC),
            seed=42,
            deterministic_budget=90.0,
            state=state,
            model_version="weekly.h1-h12.s2-s10",
        ),
        weights=dict(WEIGHTS),
        candidates=(_candidate(),) if state is RunState.COMPLETED else (),
        **kwargs,
    )


# ── rule 1: exactly one input changes (ADR-007) ────────────────────────


def test_a_weight_delta_changes_the_weights_and_nothing_else():
    new = regenerate(_record(), "c1", WeightDelta(criterion="S3", new_weight=0.30), "r2")

    assert new.weights["S3"] == 0.30
    assert {k: v for k, v in new.weights.items() if k != "S3"} == {
        k: v for k, v in WEIGHTS.items() if k != "S3"
    }
    assert new.overrides.is_empty()


def test_a_lock_changes_the_overrides_and_not_the_weights():
    new = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")

    assert new.weights == WEIGHTS
    assert new.overrides.locked_placements == frozenset({Placement("S0001", 7, "2")})
    assert not new.overrides.excluded_slots and not new.overrides.excluded_rooms


def test_an_exclusion_changes_the_overrides_and_not_the_weights():
    new = regenerate(_record(), "c1", ExcludeSlot(session="S0001", slot=7), "r2")

    assert new.weights == WEIGHTS
    assert new.overrides.excluded_slots == frozenset({("S0001", 7)})
    assert not new.overrides.locked_placements


# ── rule 2: overrides COMPOSE along the chain (C-20) ───────────────────


def test_a_second_recommendation_keeps_the_first():
    """The rule the whole of C-20 clause (iv) is about.

    Without it, accepting a second recommendation silently discards the first
    and a user watches a lock they set disappear with nothing on screen to
    explain it.
    """
    first = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")
    # r2 has now completed and produced its own candidate.
    completed = replace(first, run=replace(first.run, state=RunState.COMPLETED))
    completed = replace(completed, candidates=(_candidate("c2"),))

    second = regenerate(completed, "c2", ExcludeSlot(session="S0002", room="4"), "r3")

    assert second.overrides.locked_placements == frozenset({Placement("S0001", 7, "2")})
    assert second.overrides.excluded_rooms == frozenset({("S0002", "4")})


def test_a_second_weight_delta_reads_against_the_run_s_own_vector():
    """Rule 3, and it is rule 2 in a different disguise: reading the catalogue
    instead would discard the first delta."""
    first = regenerate(_record(), "c1", WeightDelta(criterion="S3", new_weight=0.30), "r2")
    completed = replace(
        first,
        run=replace(first.run, state=RunState.COMPLETED),
        candidates=(_candidate("c2"),),
    )

    second = regenerate(completed, "c2", WeightDelta(criterion="S5", new_weight=0.05), "r3")

    assert second.weights["S3"] == 0.30, "the first delta was discarded"
    assert second.weights["S5"] == 0.05


# ── provenance, and invariant 6 ────────────────────────────────────────


def test_the_new_run_records_where_it_came_from():
    new = regenerate(_record(), "c1", WeightDelta(criterion="S3", new_weight=0.30), "r2")

    assert new.origin is not None
    assert new.origin.run == "r1"
    assert new.origin.candidate == "c1"
    assert new.origin.action_kind == "weight_delta"
    assert "S3" in new.origin.action_detail


def test_the_origin_run_is_not_touched():
    """Invariant 6. The regenerated timetable is a NEW candidate under a NEW
    run, so nothing about the run it came from may change - including the
    record object the caller still holds."""
    origin = _record()
    before = replace(origin)

    regenerate(origin, "c1", LockSession(session="S0001"), "r2")

    assert origin == before


def test_the_new_run_starts_pending_and_carries_a_new_id():
    """It goes through the ordinary path - pre-analysis, solve, scoring - and
    cannot acquire a shortcut past any of it."""
    new = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")

    assert new.run.id == "r2"
    assert new.run.state is RunState.PENDING
    assert new.candidates == ()


def test_the_new_run_keeps_the_origin_s_seed_and_budget():
    """A regeneration answers "what changes if I change ONE input". Changing
    the seed at the same time would make the two runs incomparable."""
    new = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")

    assert new.run.seed == 42
    assert new.run.deterministic_budget == 90.0


# ── the refusals ───────────────────────────────────────────────────────


def test_regenerating_from_a_run_that_produced_nothing_is_refused():
    with pytest.raises(RegenerationError, match="nothing to regenerate from"):
        regenerate(_record(state=RunState.FAILED), "c1", LockSession(session="S0001"), "r2")


def test_a_candidate_from_another_run_is_refused():
    with pytest.raises(RegenerationError, match="is not part of run"):
        regenerate(_record(), "not-mine", LockSession(session="S0001"), "r2")


def test_a_weight_delta_on_a_criterion_the_run_does_not_price_is_refused():
    """S1, S8 and S9 are retired codes and must never be reused. Accepting one
    here would ADD an entry and score the run under a vector no other run
    uses."""
    with pytest.raises(RegenerationError, match="not one this run prices"):
        regenerate(_record(), "c1", WeightDelta(criterion="S9", new_weight=0.2), "r2")


def test_a_negative_weight_is_refused():
    """A negative weight would let a dominated candidate outscore its
    dominator, and the proof that this cannot happen is what C-14 rests on."""
    with pytest.raises(RegenerationError, match="negative"):
        regenerate(_record(), "c1", WeightDelta(criterion="S3", new_weight=-0.1), "r2")


def test_two_conflicting_locks_on_one_session_are_refused_with_both_targets():
    """Refused HERE rather than at build_variables, which also refuses but
    cannot say which recommendation contradicted which."""
    first = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")
    completed = replace(
        first,
        run=replace(first.run, state=RunState.COMPLETED),
        # The same session, placed somewhere else in r2's candidate.
        candidates=(
            Candidate(
                id="c2",
                run="r2",
                profile_name="balanced",
                cost=100,
                score=80.0,
                placements=(Placement(session="S0001", slot=9, room="1"),),
                sub_scores=(),
            ),
        ),
    )

    with pytest.raises(RegenerationError, match="already locked to slot 7 room 2"):
        regenerate(completed, "c2", LockSession(session="S0001"), "r3")


def test_relocking_a_session_to_the_same_place_is_not_a_conflict():
    """Idempotent, and worth pinning: a user re-accepting the same
    recommendation should not be told they contradicted themselves."""
    first = regenerate(_record(), "c1", LockSession(session="S0001"), "r2")
    completed = replace(
        first,
        run=replace(first.run, state=RunState.COMPLETED),
        candidates=(_candidate("c2"),),
    )

    second = regenerate(completed, "c2", LockSession(session="S0001"), "r3")

    assert second.overrides.locked_placements == frozenset({Placement("S0001", 7, "2")})


# ── the catalogue is closed, at the wire boundary ──────────────────────


def test_a_fourth_action_kind_is_refused_by_name():
    with pytest.raises(RegenerationError, match="not one of the three catalogue actions"):
        action_from_wire(kind="move_session", session="S0001", slot=3)


def test_exclude_slot_naming_both_a_slot_and_a_room_is_refused():
    with pytest.raises(RegenerationError, match="exactly one of slot or room"):
        action_from_wire(kind="exclude_slot", session="S0001", slot=3, room="4")


def test_exclude_slot_naming_neither_is_refused():
    with pytest.raises(RegenerationError, match="exactly one of slot or room"):
        action_from_wire(kind="exclude_slot", session="S0001")


def test_weight_delta_without_its_fields_is_refused():
    with pytest.raises(RegenerationError, match="requires a criterion and a new weight"):
        action_from_wire(kind="weight_delta", criterion="S3")


def test_the_three_kinds_round_trip():
    assert action_from_wire("weight_delta", criterion="S3", new_weight=0.3).kind == "weight_delta"
    assert action_from_wire("lock_session", session="S0001").kind == "lock_session"
    assert action_from_wire("exclude_slot", session="S0001", slot=3).kind == "exclude_slot"


def test_an_ordinary_run_has_no_origin_and_empty_overrides():
    """The default, asserted so that `origin is None` keeps meaning "launched
    from the generation screen" rather than "we forgot to set it"."""
    ordinary = _record()
    assert ordinary.origin is None
    assert ordinary.overrides == RunOverrides()
    assert ordinary.overrides.is_empty()
