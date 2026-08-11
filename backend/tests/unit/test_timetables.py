"""Which sessions one group is concerned by — the student surface's filter.

`tests/acceptance/test_student_view.py` verifies the right through the API.
This file holds the edge cases a screen test cannot reach: a malformed parent
chain, a placement naming a session the instance does not have, and the
ordering that makes two reads of one timetable identical.

⚠️ **The ancestor rule is the substance, not a detail.** A CM is addressed to
the promotion, so a subgroup shown only the sessions carrying its own id would
display a week with holes its students do not have — the same relation H12 uses
in the solver, reimplemented here over plain domain data because `services` may
reach neither the solver nor the analysis layer.
"""

from __future__ import annotations

import dataclasses

import pytest

from optiedt.domain.entities import Candidate, Placement, SubScore
from optiedt.services.timetables import ancestors_or_self, placements_for_group


def _candidate(*placements: Placement) -> Candidate:
    return Candidate(
        id="c1",
        run="r1",
        profile_name="balanced",
        cost=0,
        score=50.0,
        placements=placements,
        sub_scores=(SubScore(criterion="S2", raw_value=0.0, normalised=1.0),),
    )


def test_a_subgroup_reaches_itself_and_every_group_above_it(tiny_instance) -> None:
    assert ancestors_or_self("T", tiny_instance) == ("T", "G", "P")


def test_a_promotion_reaches_only_itself(tiny_instance) -> None:
    assert ancestors_or_self("P", tiny_instance) == ("P",)


def test_an_unknown_group_reaches_nothing_beyond_itself(tiny_instance) -> None:
    """Returned rather than raised: the caller has already established that the
    group exists, and inventing an ancestor for one that does not would be
    worse than an empty week."""
    assert ancestors_or_self("no-such-group", tiny_instance) == ("no-such-group",)


def test_a_parent_cycle_terminates_instead_of_hanging(tiny_instance) -> None:
    """⚠️ Why the walk is bounded rather than `while parent is not None`.

    Malformed data must produce a visibly wrong answer, never a request that
    never returns — the same reasoning `features/timetable/model.ts` gives for
    its own bound.
    """
    cyclic = dataclasses.replace(
        tiny_instance,
        groups=tuple(
            dataclasses.replace(g, parent_group="T") if g.id == "P" else g
            for g in tiny_instance.groups
        ),
    )

    chain = ancestors_or_self("T", cyclic)

    assert len(chain) <= 8


def test_a_group_gets_its_own_sessions_and_its_ancestors(tiny_instance) -> None:
    """The whole week a subgroup's students actually sit through."""
    candidate = _candidate(
        Placement(session="s_leaf", slot=0, room="R1"),
        Placement(session="s_mid", slot=1, room="R1"),
        Placement(session="s_top", slot=2, room="R2"),
    )

    kept = placements_for_group(candidate, tiny_instance, "T")

    assert [p.session for p in kept] == ["s_leaf", "s_mid", "s_top"]


def test_a_sibling_subgroups_session_is_excluded(tiny_instance) -> None:
    """⚠️ The assertion that would fail if the filter were dropped.

    Descending rather than ascending is the mistake to catch: a promotion's
    week is not the union of its subgroups', and a subgroup's week is not its
    sibling's.
    """
    with_sibling = dataclasses.replace(
        tiny_instance,
        groups=(
            *tiny_instance.groups,
            dataclasses.replace(tiny_instance.groups[2], id="T2", label="T2"),
        ),
        sessions=(
            *tiny_instance.sessions,
            dataclasses.replace(tiny_instance.sessions[0], id="s_sibling", group="T2"),
        ),
    )
    candidate = _candidate(
        Placement(session="s_leaf", slot=0, room="R1"),
        Placement(session="s_sibling", slot=1, room="R1"),
    )

    kept = placements_for_group(candidate, with_sibling, "T")

    assert [p.session for p in kept] == ["s_leaf"]


def test_a_placement_naming_an_unknown_session_is_dropped(tiny_instance) -> None:
    """It can only mean the candidate and the instance disagree, and showing a
    student a session nobody can name would be worse than omitting it."""
    candidate = _candidate(
        Placement(session="s_leaf", slot=0, room="R1"),
        Placement(session="ghost", slot=1, room="R1"),
    )

    kept = placements_for_group(candidate, tiny_instance, "T")

    assert [p.session for p in kept] == ["s_leaf"]


def test_the_week_comes_back_in_a_stable_order(tiny_instance) -> None:
    """Two reads of one timetable must be byte-identical — the same reason
    `build_declaration` sorts a teacher's grid."""
    candidate = _candidate(
        Placement(session="s_top", slot=5, room="R2"),
        Placement(session="s_leaf", slot=1, room="R1"),
        Placement(session="s_mid", slot=1, room="R2"),
    )

    kept = placements_for_group(candidate, tiny_instance, "T")

    assert [(p.slot, p.session) for p in kept] == [(1, "s_leaf"), (1, "s_mid"), (5, "s_top")]


@pytest.mark.parametrize("group", ["T", "G", "P"])
def test_every_level_of_the_chain_yields_a_week(tiny_instance, group: str) -> None:
    candidate = _candidate(
        Placement(session="s_leaf", slot=0, room="R1"),
        Placement(session="s_mid", slot=1, room="R1"),
        Placement(session="s_top", slot=2, room="R2"),
    )

    assert placements_for_group(candidate, tiny_instance, group)
