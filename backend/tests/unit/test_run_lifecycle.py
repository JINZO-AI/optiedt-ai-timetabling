"""The run state machine, and the two states Phase 4 must NOT enter.

The lifecycle is documented in docs/architecture.md and the shape matters more
than it looks: a run that jumps a state leaves the record describing a pipeline
that did not happen, and a run that enters DIAGNOSING without a diagnosis run
would report a conflict set nobody computed.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from optiedt.domain.enums import RunState
from optiedt.services.runs import (
    ALLOWED_TRANSITIONS,
    MODEL_VERSION,
    TERMINAL_STATES,
    IllegalTransitionError,
    InMemoryRunStore,
    RunRequest,
    check_transition,
    new_run_record,
)

REQUEST = RunRequest(seed=42, deterministic_budget=90.0)
WEIGHTS = {"S2": 0.25, "S3": 0.15}


# ── the machine ────────────────────────────────────────────────────────


def test_a_new_run_is_pending_and_records_what_produced_it() -> None:
    r = new_run_record("r1", REQUEST, WEIGHTS)
    assert r.state is RunState.PENDING
    assert r.run.seed == 42
    assert r.run.deterministic_budget == 90.0
    assert r.run.model_version == MODEL_VERSION
    assert r.weights == WEIGHTS
    assert r.candidates == ()


def test_the_happy_path_is_the_documented_one() -> None:
    r = new_run_record("r1", REQUEST, WEIGHTS)
    for target in (
        RunState.PREANALYSIS,
        RunState.SOLVING,
        RunState.SCORING,
        RunState.COMPLETED,
    ):
        r = r.to(target)
    assert r.state is RunState.COMPLETED


def test_infeasible_bypasses_scoring() -> None:
    """There is nothing to score: no profile produced a timetable."""
    r = new_run_record("r1", REQUEST, WEIGHTS).to(RunState.PREANALYSIS).to(RunState.SOLVING)
    assert r.to(RunState.INFEASIBLE).state is RunState.INFEASIBLE
    with pytest.raises(IllegalTransitionError):
        r.to(RunState.COMPLETED)


def test_a_run_cannot_skip_a_state() -> None:
    r = new_run_record("r1", REQUEST, WEIGHTS)
    with pytest.raises(IllegalTransitionError):
        r.to(RunState.SOLVING)
    with pytest.raises(IllegalTransitionError):
        r.to(RunState.COMPLETED)


def test_terminal_states_admit_nothing_further() -> None:
    for state in TERMINAL_STATES:
        assert ALLOWED_TRANSITIONS[state] == frozenset()


def test_infeasible_is_not_terminal_because_diagnosis_leaves_from_it() -> None:
    assert RunState.INFEASIBLE not in TERMINAL_STATES
    assert ALLOWED_TRANSITIONS[RunState.INFEASIBLE] == frozenset({RunState.DIAGNOSING})


def test_diagnosing_is_reachable_only_from_infeasible() -> None:
    """The diagnosis branch is entered ONLY when no timetable exists."""
    sources = [s for s, targets in ALLOWED_TRANSITIONS.items() if RunState.DIAGNOSING in targets]
    assert sources == [RunState.INFEASIBLE]


def test_failure_is_reachable_from_every_state_that_does_work() -> None:
    for state in (
        RunState.PENDING,
        RunState.PREANALYSIS,
        RunState.SOLVING,
        RunState.SCORING,
        RunState.DIAGNOSING,
    ):
        assert RunState.FAILED in ALLOWED_TRANSITIONS[state]


def test_every_state_has_an_entry() -> None:
    """A state absent from the table would raise KeyError on transition."""
    assert set(ALLOWED_TRANSITIONS) == set(RunState)


def test_check_transition_accepts_a_legal_move() -> None:
    check_transition(RunState.PENDING, RunState.PREANALYSIS)


# ── the store ──────────────────────────────────────────────────────────


def test_store_round_trip_and_duplicate_refusal() -> None:
    store = InMemoryRunStore()
    r = new_run_record("r1", REQUEST, WEIGHTS)
    store.create(r)
    assert store.get("r1") == r
    assert store.get("missing") is None
    with pytest.raises(KeyError):
        store.create(r)


def test_saving_replaces_the_revision() -> None:
    store = InMemoryRunStore()
    r = new_run_record("r1", REQUEST, WEIGHTS)
    store.create(r)
    store.save(r.to(RunState.PREANALYSIS))
    saved = store.get("r1")
    assert saved is not None
    assert saved.state is RunState.PREANALYSIS


def test_runs_are_listed_newest_first() -> None:
    # created_at is set explicitly: two runs made in the same tick would
    # otherwise leave the order to a stable sort on equal keys, and the test
    # would pass or fail on clock resolution rather than on the behaviour.
    store = InMemoryRunStore()
    first = new_run_record("r1", REQUEST, WEIGHTS)
    second = new_run_record("r2", REQUEST, WEIGHTS)
    first = replace(first, run=replace(first.run, created_at=datetime(2026, 8, 1, tzinfo=UTC)))
    second = replace(second, run=replace(second.run, created_at=datetime(2026, 8, 2, tzinfo=UTC)))
    store.create(first)
    store.create(second)
    assert [r.run.id for r in store.all()] == ["r2", "r1"]
