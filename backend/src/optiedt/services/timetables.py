"""Which sessions one group is actually concerned by.

SRS Table 2 gives the student *"read the timetable of their group"*, and this
module is the *their group* half of that sentence — computed on the server,
because a payload carrying every group's placements with the browser filtering
for display would be granting the student every group's week and calling the
difference presentation.

⚠️ **A group's timetable includes its ancestors' sessions.** The chain is
promotion → tutorial group → laboratory subgroup, and a CM is addressed to the
promotion: a subgroup shown only the sessions carrying its own id would display
a week with holes its students do not have. This is the same relation H12 uses
in the solver and `features/timetable/model.ts` applies for the other views —
reimplemented over plain domain data, as the analysis layer does, because
`services` may not reach into either.
"""

from __future__ import annotations

from optiedt.domain.entities import Candidate, GroupId, Placement
from optiedt.domain.instance import Instance

MAX_GROUP_DEPTH = 8
"""The chain is three levels; the bound is a guard, not a limit.

Bounded rather than walked with `while parent is not None` for the reason
`features/timetable/model.ts` gives: a malformed parent cycle in the data would
otherwise hang the request instead of returning a wrong answer visibly.
"""


def ancestors_or_self(group: GroupId, instance: Instance) -> tuple[GroupId, ...]:
    """A group and every group above it, promotion last."""
    parent_of = {g.id: g.parent_group for g in instance.groups}
    chain: list[GroupId] = []
    current: GroupId | None = group
    for _ in range(MAX_GROUP_DEPTH):
        if current is None:
            break
        chain.append(current)
        current = parent_of.get(current)
    return tuple(chain)


def placements_for_group(
    candidate: Candidate, instance: Instance, group: GroupId
) -> tuple[Placement, ...]:
    """The placements that group's students attend, in slot order.

    Ordered so that two reads of one timetable are byte-identical — the same
    reason `build_declaration` sorts a teacher's grid. A placement whose
    session is unknown to the instance is dropped rather than guessed at: it
    can only mean the candidate and the instance disagree, and showing a
    student a session nobody can name would be worse than omitting it.
    """
    reaching = set(ancestors_or_self(group, instance))
    group_of = {s.id: s.group for s in instance.sessions}
    return tuple(
        sorted(
            (p for p in candidate.placements if group_of.get(p.session) in reaching),
            key=lambda p: (p.slot, p.session),
        )
    )
