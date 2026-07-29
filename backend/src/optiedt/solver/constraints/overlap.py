"""H1 and H12 - NoOverlap over intervals partitioned by a fixed data attribute.

H1 partitions sessions by teacher_id: a flat partition, one NoOverlap set
per teacher.

H12 is NOT a flat partition by promotion - that was tried first and is
wrong. Grouping every session under a promotion into one NoOverlap set
also forces unrelated siblings to mutually exclude: two different TP
subgroups of two different TD groups would be forbidden from running at
the same time, even though they are disjoint sets of students who
obviously can. The reference instance is genuinely infeasible under that
reading - not because the DATA is wrong (all five pre-analysis checks
pass on it), but because the constraint was too strong. Caught by solving
progressively smaller subsets of the constraints against the real
instance before trusting the full model, exactly per the project's
philosophy that at this occupancy an over-tight model looks identical to
an unsolvable instance.

The actual relation, matching constraint_catalogue.csv's own description
of H12 ("Parent busy => children busy (and vice-versa)"), is
ancestor-or-self: two sessions conflict iff one's group is an ancestor of
the other's group, or they are the same group. Sessions on sibling
branches (different children of the same parent) never conflict via H12,
regardless of how deep the hierarchy or how many groups it shares an
ultimate promotion with.

Implemented per group rather than per session: for each group g, gather
the sessions on g together with the sessions on every ancestor of g (not
descendants - each descendant already gathers g when it is g's turn), and
NoOverlap that set. Because every group's own set always includes itself
first, this still forces same-group exclusivity - which is why H2 (see
noop.py) remains fully subsumed even after this correction.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from optiedt.domain.entities import ConstraintCode, GroupId, SessionId
    from optiedt.domain.instance import Instance
    from optiedt.solver.variables import Variables


def _noverlap_by_key(
    model: cp_model.CpModel,
    variables: Variables,
    instance: Instance,
    key_of_session: dict[SessionId, str],
) -> None:
    by_key: dict[str, list[cp_model.IntervalVar]] = defaultdict(list)
    for session in instance.sessions:
        key = key_of_session[session.id]
        by_key[key].append(variables.interval[session.id])
    for intervals in by_key.values():
        if len(intervals) > 1:
            model.add_no_overlap(intervals)


def _ancestor_chain(group_id: GroupId, parent_of: dict[GroupId, GroupId | None]) -> list[GroupId]:
    """[group_id, parent, grandparent, ..., root]. Relies on the group
    hierarchy being a genuine forest (no cycles), which is exactly what
    the group-hierarchy pre-analysis check already verifies independently
    - see docs/data-and-instance.md, verification 5."""
    chain = []
    current: GroupId | None = group_id
    while current is not None:
        chain.append(current)
        current = parent_of.get(current)
    return chain


@dataclass(frozen=True, slots=True)
class H1:
    """A teacher has at most one session per slot: NoOverlap per teacher."""

    @property
    def code(self) -> ConstraintCode:
        return "H1"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        key_of_session = {s.id: s.teacher for s in instance.sessions}
        _noverlap_by_key(model, variables, instance, key_of_session)


@dataclass(frozen=True, slots=True)
class H12:
    """A group and every ancestor in its hierarchy are never busy together:
    per group, NoOverlap over that group's own sessions plus every
    ancestor's - never a sibling's or a cousin's."""

    @property
    def code(self) -> ConstraintCode:
        return "H12"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        parent_of = {g.id: g.parent_group for g in instance.groups}
        sessions_by_group: dict[GroupId, list[SessionId]] = defaultdict(list)
        for session in instance.sessions:
            sessions_by_group[session.group].append(session.id)

        for group in instance.groups:
            chain = _ancestor_chain(group.id, parent_of)
            intervals = [
                variables.interval[session_id]
                for ancestor_id in chain
                for session_id in sessions_by_group.get(ancestor_id, [])
            ]
            if len(intervals) > 1:
                model.add_no_overlap(intervals)
