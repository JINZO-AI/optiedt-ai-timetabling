"""FR-3 — generate a timetable respecting H1-H12.

    Acceptance criterion (SRS §8.6 Table 35, docs/testing-strategy.md §4):
    "Generation on the reference instance → no violation of a hard constraint."

    And the SRS §3.2 Table 6 row the same requirement carries:
    input  "Data of the department and availability"
    output "One slot and one room assigned to each session"

    And the criterion in docs/status.md:
    "No hard-constraint violation on the reference instance."

⚠️ **Every rule is re-derived from the placements, never taken from CP-SAT's
status.** A solver reporting FEASIBLE proves that the model it built is
satisfied; it says nothing about whether that model is the twelve rules the
department was promised. `tests/integration/test_h1_h12.py` makes the same
check against the engine directly and in more depth; this file makes it
against the timetable **a user obtains through the API**, which is what the
acceptance criterion is about.

⚠️ **All twelve codes are named as `constraint_catalogue.csv` numbers them, and
that was not true before Phase 10.** The file checked seven rules and named two
of them wrongly - the room-type check was called H5 (it is **H4**) and the
availability check H7 (it is **H6**). A test asserting the right behaviour under
the wrong code cannot support a claim of the form "respecting H1-H12": a reader
auditing the twelve ticks rules that were never checked and misses ones that
were. The catalogue is the authority on which code is which, not this file and
not the PDFs.

⚠️ **H2 and H11 are checked even though the solver posts neither.** Both are
subsumed - H2 by H12, H11 by H3 plus H7 (`solver/constraints/noop.py`) - but
what FR-3 promises the department is the twelve *statements*, not twelve
postings. If H12's grouping were ever narrowed, H2 is the assertion that would
notice.

⚠️ **H10 is the one rule this run cannot exercise**, because the reference
instance locks nothing. That is asserted below rather than assumed, so the day
a locked session appears in the data the vacuity stops being silent.
`tests/integration/test_h10_locks.py` is what exercises H10 for real.

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


def test_h7_each_session_is_placed_exactly_once_in_one_slot_and_one_room(
    generated: dict[str, object], instance
) -> None:
    """H7, and with it SRS §3.2 Table 6's output row.

    The row says "one slot **and one room** assigned to each session", so the
    room half is asserted too: a placement carrying a session and a slot but a
    room id the instance does not define would satisfy every overlap rule below
    and still not be a timetable anyone can use.
    """
    placements = _placements(generated)
    placed = [p["session"] for p in placements]
    room_ids = {r.id for r in instance.rooms}
    slot_indices = {s.index for s in instance.slots}

    assert sorted(placed) == sorted(s.id for s in instance.sessions)
    assert len(placed) == len(set(placed)) == 218, "a session placed twice, or one missing"

    for placement in placements:
        assert placement["slot"] in slot_indices, f"{placement['session']}: slot off the calendar"
        assert placement["room"] in room_ids, f"{placement['session']}: no such room"


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


def test_h2_no_group_attends_two_of_its_own_sessions_at_once(
    generated: dict[str, object], instance
) -> None:
    """H2, checked although the solver posts nothing for it.

    `solver/constraints/noop.py` records H2 as a strict subset of H12: H12's
    NoOverlap covers every session in a promotion's hierarchy, and a group is
    part of its own. That makes the *posting* redundant, not the *promise* -
    FR-3 owes the department twelve statements. This is the assertion that
    would notice if H12's grouping were ever narrowed to, say, ancestors only.
    """
    by_session = {s.id: s for s in instance.sessions}
    occupied: dict[tuple[str, int], str] = {}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            key = (session.group, period)
            assert key not in occupied, (
                f"H2: group {session.group} has {placement['session']} and "
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


def test_h4_every_session_is_in_a_room_of_the_type_it_requires(
    generated: dict[str, object], instance
) -> None:
    """H4 in the catalogue - this test was called `test_h5_...` until Phase 10.

    H5 is room *capacity*, which is the test below. Two different rules, and
    the instance can satisfy one while breaking the other.
    """
    by_session = {s.id: s for s in instance.sessions}
    room_type = {r.id: r.type for r in instance.rooms}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        assert room_type[placement["room"]] == session.required_room_type


def test_h5_every_room_is_large_enough_for_the_group_it_holds(
    generated: dict[str, object], instance
) -> None:
    """H5 - "room capacity >= group size", and nothing in this file checked it.

    Distinct from H4: `Lab_Info` rooms are interchangeable by type, so a
    type-correct assignment can still seat a 40-student promotion in a room
    built for 20. The solver prunes on it (`constraints/domain_pruned.py`); this
    re-derives it from the sizes the instance declares.
    """
    by_session = {s.id: s for s in instance.sessions}
    group_size = {g.id: g.size for g in instance.groups}
    capacity = {r.id: r.capacity for r in instance.rooms}

    for placement in _placements(generated):
        session = by_session[placement["session"]]
        seats = capacity[placement["room"]]
        needed = group_size[session.group]
        assert seats >= needed, (
            f"H5: {placement['session']} seats {needed} in {placement['room']}, which holds {seats}"
        )


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


def test_h10_this_run_locks_nothing_so_the_rule_is_vacuous_here(
    generated: dict[str, object], instance
) -> None:
    """H10 is the one rule the reference instance cannot exercise.

    ⚠️ **Asserted rather than assumed.** "No session is locked, so H10 holds
    trivially" is only true while it is true, and a lock arriving in
    `sessions.csv` would turn a vacuous pass into a silent one. This fails the
    day that happens, which is when someone should be pointed at
    `tests/integration/test_h10_locks.py` - the file that exercises H10 against
    the real solver, including the limiting case of all 218 placements locked.
    """
    locked = [s.id for s in instance.sessions if s.locked]
    overrides = generated["overrides"]

    assert locked == [], (
        f"{len(locked)} session(s) are now locked, so H10 is no longer vacuous "
        "here and this file must check the placements honour them"
    )
    assert overrides["lockedPlacements"] == [], "an ordinary run solves under no lock"


def test_h11_no_room_type_is_asked_for_more_rooms_than_it_has(
    generated: dict[str, object], instance
) -> None:
    """H11, checked although the solver posts nothing for it either.

    `noop.py` derives it from H3 plus H7: if every room of a type has its own
    NoOverlap and every session takes exactly one compatible room, no more
    sessions of a type can run at once than there are rooms of it. That is an
    argument, and this is the measurement - counted per period, per type, which
    is the form the requirement states ("sum of demand <= room capacity").
    """
    by_session = {s.id: s for s in instance.sessions}
    rooms_of_type: dict[object, int] = defaultdict(int)
    for room in instance.rooms:
        rooms_of_type[room.type] += 1

    demand: dict[tuple[object, int], int] = defaultdict(int)
    for placement in _placements(generated):
        session = by_session[placement["session"]]
        for period in range(placement["slot"], placement["slot"] + session.duration_periods):
            demand[(session.required_room_type, period)] += 1

    for (room_type, period), needed in demand.items():
        available = rooms_of_type[room_type]
        assert needed <= available, (
            f"H11: {needed} sessions need a {room_type} at period {period}, "
            f"and there are {available}"
        )


def test_h6_the_teacher_declarations_in_the_instance_are_honoured(
    generated: dict[str, object], instance
) -> None:
    """H6 in the catalogue - this test's docstring said H7 until Phase 10.

    H7 is "each session placed exactly once", which is the first test in this
    file. The instance carries 157 declarations, all unavailability.
    """
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
                f"H6: {session.teacher} declared period {period} unavailable"
            )
