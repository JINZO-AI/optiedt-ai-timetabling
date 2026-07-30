"""y[s][t] - "session s occupies slot t" - and the start indicators behind it.

This is the accounting layer the objective reads. It places nothing: every
variable here is channelled from start[s], which solver/variables.py already
built and which the hard constraints already own. Nothing in this module may
narrow a domain or forbid a placement - if it ever does, a soft criterion has
silently become a hard one.

C-7, resolved 2026-07-30 (docs/open-questions.md). The specification names
y[s][t] and attributes H7 to it, but never writes the constraint linking it to
start[s] - and with 104 of the 218 sessions spanning two periods that link is
not obvious, because y must mean OCCUPIES t, not STARTS AT t.

The encoding, per session s with duration d and pruned start domain D(s):

    x[s,t0]                        one boolean per valid start t0
    exactly_one(x[s,t0])           s starts somewhere
    start[s] == sum(t0 * x[s,t0])  channel to the integer variables.py built
    y[s,t] == sum(x[s,t0] for t0 in D(s) if t0 <= t <= t0 + d - 1)

The last line is uniform in d: for a 1-period session y[s,t] collapses to
x[s,t]; for a 2-period session it is x[s,t-1] + x[s,t]. exactly_one makes at
most one term of any such sum true, so the sum is always 0 or 1 and the
equality is exact - no inequality pair, no big-M, no reified disjunction.

Reifying against the interval instead (y[s,t] => start[s] in [t-d+1, t], plus
the negation, via only_enforce_if) would avoid x, but costs two constraints
per pair instead of one and propagates worse: nothing then ties one session's
y values to each other, so the solver can leave several unfixed while start[s]
is already decided. exactly_one is the standard direct encoding of an integer
variable and CP-SAT's presolve exploits it.

x is not scaffolding. S5 (preferred windows) and S7 (subject spread) are
properties of where a session STARTS, and S4 (extra working day) of which days
it touches; expressing those over x is direct, while expressing them over y
means undoing the double-counting a 2-period session introduces.

⚠️ Built on demand. The Phase 2 feasibility solve does not call this, and must
not: it is measured at ~3s and there is no reason to pay for thousands of
booleans no constraint reads until the objective exists. engine.py calls
build_occupancy() only when it has an objective to encode.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from optiedt.domain.entities import SessionId, SlotIndex
from optiedt.domain.instance import Instance
from optiedt.solver.variables import Variables


@dataclass(slots=True)
class Occupancy:
    """The accounting variables. Read by the objective, written by nothing."""

    starts_at: dict[tuple[SessionId, SlotIndex], cp_model.IntVar]
    """x[s, t0] is 1 iff session s begins at slot t0. Defined for exactly the
    starts variables.py left in s's domain after H6/H8/H9 pruning, so a key
    absent here is a start the hard constraints already excluded - not an
    oversight."""

    occupies: dict[tuple[SessionId, SlotIndex], cp_model.IntVar]
    """y[s, t] is 1 iff session s occupies slot t - covering BOTH periods of a
    2-period session, not just the one it starts in. Defined only for (s, t)
    some valid start of s can actually reach; a pair no start covers is
    constant 0 and is omitted rather than posted. That omission is why the
    real count sits well below the 6,104 upper bound quoted in
    docs/constraint-model.md."""

    def occupied_slots(self, session_id: SessionId) -> tuple[SlotIndex, ...]:
        """The slots session_id could occupy, ascending. The support of
        y[session_id, ...] - useful to a criterion that needs to iterate a
        session's reachable slots without rediscovering the pruning."""
        return tuple(sorted(t for (s, t) in self.occupies if s == session_id))


def build_occupancy(model: cp_model.CpModel, variables: Variables, instance: Instance) -> Occupancy:
    """Build x[s,t0] and y[s,t], channelled to the existing start[s].

    Adds constraints, but only ones that are consequences of start[s]: every
    solution of the model without this call extends to exactly one solution
    with it. It therefore cannot make a feasible model infeasible, which is
    the property that lets the objective be encoded without any risk to
    correctness of the placement.
    """
    starts_at: dict[tuple[SessionId, SlotIndex], cp_model.IntVar] = {}
    occupies: dict[tuple[SessionId, SlotIndex], cp_model.IntVar] = {}

    for session in instance.sessions:
        start = variables.start[session.id]
        valid_starts = _domain_values(start)
        duration = session.duration_periods

        indicators = []
        for slot in valid_starts:
            indicator = model.new_bool_var(f"x[{session.id},{slot}]")
            starts_at[(session.id, slot)] = indicator
            indicators.append(indicator)

        # s starts somewhere, and start[s] agrees with which indicator is set.
        model.add_exactly_one(indicators)
        model.add(start == sum(slot * starts_at[(session.id, slot)] for slot in valid_starts))

        # y[s,t]: the starts that would place s over t are those in
        # [t - duration + 1, t]. Only slots some valid start reaches get a
        # variable at all - the rest are constant 0.
        covering: dict[SlotIndex, list[cp_model.IntVar]] = {}
        for slot in valid_starts:
            for offset in range(duration):
                covering.setdefault(slot + offset, []).append(starts_at[(session.id, slot)])

        for slot, sources in sorted(covering.items()):
            occupied = model.new_bool_var(f"y[{session.id},{slot}]")
            occupies[(session.id, slot)] = occupied
            model.add(occupied == sum(sources))

    return Occupancy(starts_at=starts_at, occupies=occupies)


def _domain_values(variable: cp_model.IntVar) -> list[SlotIndex]:
    """The values left in an IntVar's domain, ascending.

    variables.py builds start[s] from an explicit value list (H6/H8/H9
    pruning), so the domain is the authority on which starts are legal and
    this module never re-derives that rule. Reading it back keeps the two in
    step by construction: a change to the pruning cannot leave x[s,t0]
    describing starts the model no longer permits.
    """
    flat = list(variable.proto.domain)  # a proto repeated field, not sliceable
    values: list[SlotIndex] = []
    for lower, upper in zip(flat[::2], flat[1::2], strict=True):
        values.extend(range(lower, upper + 1))
    return values
