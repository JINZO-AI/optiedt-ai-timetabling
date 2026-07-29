"""H1 and H12 — NoOverlap over intervals partitioned by a fixed data attribute.

Both partition sessions by something already known before solving (the
teacher for H1, the promotion for H12), unlike H3 (room_assignment.py),
where the partition key - room[s] - is a decision variable the solver
hasn't chosen yet. That difference is why these two share one
straightforward construction while H3 needs the optional-interval pattern.

H12's partition key is the promotion, not a walk up the parent-group
chain: every row of groups.csv carries its own promotion_id directly,
including TD and TP rows, so grouping sessions by
group_by_id[session.group].promotion already gathers every session
anywhere in that promotion's hierarchy into one NoOverlap set. That set
is a superset of what H2 alone would forbid for any single group, which
is the concrete reason H2 needs no separate posting (see noop.py).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ortools.sat.python import cp_model

    from optiedt.domain.entities import ConstraintCode, SessionId
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
        model.add_no_overlap(intervals)


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
    """A promotion and its whole group hierarchy are never busy together:
    NoOverlap per promotion, over every session in any group under it."""

    @property
    def code(self) -> ConstraintCode:
        return "H12"

    @property
    def carries_assumption_literal(self) -> bool:
        return True

    def apply(self, model: cp_model.CpModel, variables: Variables, instance: Instance) -> None:
        promotion_by_group = {g.id: g.promotion for g in instance.groups}
        key_of_session = {s.id: promotion_by_group[s.group] for s in instance.sessions}
        _noverlap_by_key(model, variables, instance, key_of_session)
