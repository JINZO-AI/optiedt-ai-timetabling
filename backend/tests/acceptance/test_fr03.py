"""FR-3 — generate a timetable respecting H1-H12.

    Acceptance criterion (docs/testing-strategy.md §4):
    "Generate on the reference instance → no hard-constraint violation."

    And the criterion in docs/status.md:
    "No hard-constraint violation on the reference instance."

⚠️ **Every rule is re-derived from the placements, never taken from CP-SAT's
status.** A solver reporting FEASIBLE proves that the model it built is
satisfied; it says nothing about whether that model is the twelve rules the
department was promised. `tests/integration/test_h1_h12.py` makes the same
check against the engine directly and in more depth; this file makes it
against the timetable **a user obtains through the API**, which is what the
acceptance criterion is about.

Real solver, marked `solver`: a fake placing sessions wherever it likes would
verify the fake.
"""

from __future__ import annotations

from collections import defaultdict

import pytest

from optiedt.api import deps

pytestmark = [pytest.mark.acceptance, pytest.mark.solver]


@pytest.fixture(scope="module")
def instance():
    deps.get_instance.cache_clear()
    return deps.get_instance()


@pytest.fixture
def generated(production_portfolio: dict[str, object]) -> dict[str, object]:
    """The run every engine-level criterion shares (see acceptance/conftest.py).

    ⚠️ **A smaller budget does not just run faster - it fails.** An earlier
    revision used a total of 9, reasoning from the 2.8-3.3 s "first valid
    timetable" figure; that figure is a FEASIBILITY solve with every weight at
    zero. Through the portfolio the total is divided between three profiles and
    each carries the objective, so 9 gives 3 per profile and CP-SAT returns
    `UNKNOWN` - the run lands in `FAILED` and the engine refuses to present it
    as an answer. Measured, not guessed.
    """
    return production_portfolio


def _placements(run: dict[str, object]) -> list[dict[str, object]]:
    candidates = run["candidates"]
    assert isinstance(candidates, list) and candidates
    return list(candidates[0]["placements"])


def test_a_timetable_is_produced_with_every_session_placed(
    generated: dict[str, object], instance
) -> None:
    placed = {p["session"] for p in _placements(generated)}

    assert placed == {s.id for s in instance.sessions}
    assert len(placed) == 218


def test_h1_no_teacher_is_in_two_places_at_once(generated: dict[str, object], instance) -> None:
    by_session = {s.id: s for s in instance.sessions}
    occupied: dict[tuple[str, int], str] = {}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            key = (session.teacher, period)
            assert key not in occupied, (
                f"H1: teacher {session.teacher} in {placement['session']} and "
                f"{occupied[key]} at period {period}"
            )
            occupied[key] = placement["session"]


def test_h3_no_room_holds_two_sessions_at_once(generated: dict[str, object], instance) -> None:
    by_session = {s.id: s for s in instance.sessions}
    occupied: dict[tuple[str, int], str] = {}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            key = (placement["room"], period)
            assert key not in occupied, (
                f"H3: room {placement['room']} holds {placement['session']} and "
                f"{occupied[key]} at period {period}"
            )
            occupied[key] = placement["session"]


def test_h5_every_session_is_in_a_room_of_the_type_it_requires(
    generated: dict[str, object], instance
) -> None:
    by_session = {s.id: s for s in instance.sessions}
    room_type = {r.id: r.type for r in instance.rooms}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        assert room_type[placement["room"]] == session.required_room_type


def test_h8_a_two_period_session_does_not_cross_a_day_boundary(
    generated: dict[str, object], instance
) -> None:
    """The rule C-13 turned on. A 5-period day cannot be tiled by 2-period
    sessions, which is what made the original instance infeasible - so a
    violation here would look like extra capacity that does not exist."""
    by_session = {s.id: s for s in instance.sessions}
    day_of = {s.index: s.day_index for s in instance.slots}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        span = range(placement["slot"], placement["slot"] + session.duration_periods)
        assert len({day_of[period] for period in span}) == 1, (
            f"H8: {placement['session']} spans two days"
        )


def test_h9_nothing_is_placed_in_a_closed_slot(generated: dict[str, object], instance) -> None:
    """The mechanism ADR-003 rests on: a closed half-day is configuration, and
    H9 is what removes it from every session's domain. FR-9's own criterion
    checks that closing one MORE slot takes effect without a code change."""
    by_session = {s.id: s for s in instance.sessions}
    open_slots = {s.index for s in instance.slots if s.is_open}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            assert period in open_slots, f"H9: {placement['session']} occupies closed slot {period}"


def test_h12_no_group_is_in_two_places_at_once_including_its_ancestors(
    generated: dict[str, object], instance
) -> None:
    """Ancestor-or-self, because a CM gathers the whole promotion.

    For each group, the sessions reaching it are its own plus every ANCESTOR's.
    A subgroup checked only against its own sessions would pass while its
    students sat in two rooms at once - which is what H12 exists to forbid.

    ⚠️ **Sibling branches do NOT conflict, and the first version of this test
    said they did.** It walked each session's ancestors and marked them
    occupied, so two different TP subgroups of one TD group appeared to clash -
    they are disjoint sets of students and obviously can run at once. It failed
    on a correct timetable (`group 2 reached by S0007 and S0006`) and the
    product was right.

    That is the same wrong reading `solver/constraints/overlap.py` records as
    tried and rejected in Phase 2, where it made the reference instance look
    genuinely infeasible. Reproducing it here, from the same plausible
    intuition, is why the docstring in that module exists - read it before
    changing this.
    """
    by_session = {s.id: s for s in instance.sessions}
    parent = {g.id: g.parent_group for g in instance.groups}
    placement_of = {p["session"]: p for p in _placements(generated)}

    def ancestors_or_self(group: str) -> list[str]:
        chain, current = [], group
        while current is not None:
            chain.append(current)
            current = parent.get(current)
        return chain

    sessions_by_group: dict[str, list[str]] = defaultdict(list)
    for session in instance.sessions:
        sessions_by_group[session.group].append(session.id)

    for group in instance.groups:
        occupied: dict[int, str] = {}
        reaching = [
            session_id
            for ancestor in ancestors_or_self(group.id)
            for session_id in sessions_by_group.get(ancestor, [])
        ]
        for session_id in reaching:
            placement = placement_of[session_id]
            duration = by_session[session_id].duration_periods
            for period in range(placement["slot"], placement["slot"] + duration):
                assert period not in occupied, (
                    f"H12: group {group.id} is reached by {session_id} and "
                    f"{occupied[period]} at period {period}"
                )
                occupied[period] = session_id


def test_the_teacher_declarations_in_the_instance_are_honoured(
    generated: dict[str, object], instance
) -> None:
    """H7. The instance carries 157 declarations, all unavailability."""
    from optiedt.domain.enums import AvailabilityState

    by_session = {s.id: s for s in instance.sessions}
    unavailable = {
        (a.teacher, a.slot)
        for a in instance.availability
        if a.state is AvailabilityState.UNAVAILABLE
    }
    assert unavailable, "the reference instance carries 157 unavailability rows"

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            assert (session.teacher, period) not in unavailable, (
                f"H7: {session.teacher} declared period {period} unavailable"
            )
