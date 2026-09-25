"""Diagnosis by relaxation: the cheapest set of data changes that admits a complete timetable.

Requirements that come from data rather than physics become elastic, each with a cost per
unit (docs/design/optimization-model.md §8): unavailability of instructors, students and
activities, closed slots, hard slot rules, room compatibility, fixed placements, the
different-days requirement and every other hard rule. Physics stays hard: nobody is in two
places, a room hosts one session at a time and is closed when it is closed, and a session
neither runs past the day nor across a break.

The search first minimizes unscheduled periods (what no relaxation can fix), then the total
cost of relaxations. The result lists every change the relaxed timetable relies on.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass, field

from optiedt.problem.atoms import atoms_of_groups
from optiedt.problem.catalog import UNSCHEDULED
from optiedt.problem.model import Problem, Session
from optiedt.problem.solution import Placement
from optiedt.solver.domains import SLOT_RULES, Context, SessionDomain, rule_slots
from optiedt.solver.engine import ProgressEvent, Runner, SolveSettings, TierOutcome
from optiedt.solver.heuristic import construct
from optiedt.solver.model import LinearExpr, ScheduleModel

COSTS = {
    "slot_closed": 50,
    "instructor_unavailable": 10,
    "students_unavailable": 10,
    "activity_unavailable": 10,
    "slot_rule": 10,
    "fixed_moved": 30,
    "room_type": 20,
    "room_features": 20,
    "room_capacity": 5,
    "room_location": 20,
    "room_not_allowed": 20,
    "oversized_room": 1,
    "different_days": 10,
    "rule": 10,
}
"""Cost of one unit of each relaxation: per period for time relaxations, per placement for
room relaxations and moved fixed placements (per missing seat for capacity), per violation
unit for rules and per extra same-day occurrence for different days."""

MAX_RELAXED_ROOMS = 15
FIRST_PHASE_SHARE = 0.4


@dataclass(frozen=True, slots=True)
class Need:
    """One data change a relaxed start or room relies on."""

    kind: str
    subject: int | None
    """Index of the instructor, group, activity, rule or room concerned (per ``kind``)."""
    slot: int | None
    cost: int


@dataclass
class Change:
    """A data change the relaxed timetable relies on, with the sessions that need it."""

    kind: str
    cost: int
    sessions: list[int] = field(default_factory=list)
    slots: list[int] = field(default_factory=list)
    subject: int | None = None
    units: int = 0
    message: str = ""


@dataclass
class RelaxationResult:
    complete: bool
    """Every session is placed in the relaxed timetable."""
    unscheduled: list[int]
    total_cost: int
    changes: list[Change]
    placements: dict[int, Placement]
    phases: list[TierOutcome]
    cancelled: bool
    warnings: list[str]
    log_tail: list[str]


@dataclass
class RelaxedDomains:
    context: Context
    start_needs: list[dict[int, tuple[Need, ...]]]
    room_needs: list[dict[int, tuple[Need, ...]]]


def relaxed_domains(context: Context) -> RelaxedDomains:
    """Every physically possible start and every plausible room of each session, with the
    data changes each one needs."""
    p = context.problem
    group_atoms = atoms_of_groups(context.atoms, len(p.groups))
    hard_slot_rules = [
        (index, rule, rule_slots(p, rule.type, rule.params))
        for index, rule in enumerate(p.rules)
        if rule.enforcement == "hard" and rule.type in SLOT_RULES
    ]
    domains: list[SessionDomain] = []
    start_needs: list[dict[int, tuple[Need, ...]]] = []
    room_needs: list[dict[int, tuple[Need, ...]]] = []
    for session, domain in zip(p.sessions, context.domains, strict=True):
        atoms = context.session_atoms[session.index]
        groups = [g.index for g in p.groups if g.unavailable and atoms & group_atoms[g.index]]
        rules = [
            (index, rule_slots_)
            for index, rule, rule_slots_ in hard_slot_rules
            if session.activity in {p.activity_index.get(a) for a in rule.activity_ids}
            or set(session.instructors)
            & {p.instructor_index[i] for i in rule.instructor_ids if i in p.instructor_index}
            or any(
                atoms & group_atoms[p.group_index[g]] for g in rule.group_ids if g in p.group_index
            )
        ]
        starts = _start_needs(p, session, groups, rules)
        rooms = _room_needs(context, session, domain)
        domains.append(
            SessionDomain(
                starts=tuple(sorted(starts)),
                rooms=tuple(rooms),
                compatible_rooms=tuple(rooms),
            )
        )
        start_needs.append(starts)
        room_needs.append(rooms)
    return RelaxedDomains(dataclasses.replace(context, domains=domains), start_needs, room_needs)


def _start_needs(
    p: Problem,
    session: Session,
    groups: list[int],
    rules: list[tuple[int, frozenset[int]]],
) -> dict[int, tuple[Need, ...]]:
    activity = p.activities[session.activity]
    result: dict[int, tuple[Need, ...]] = {}
    for day in range(p.n_days):
        for period in range(p.n_periods - session.duration + 1):
            if not all(p.joins_next[period + k] for k in range(session.duration - 1)):
                continue
            start = p.slot(day, period)
            needs: list[Need] = []
            for slot in range(start, start + session.duration):
                if slot not in p.open_slots:
                    needs.append(Need("slot_closed", None, slot, COSTS["slot_closed"]))
                for i in session.instructors:
                    if slot in p.instructors[i].unavailable:
                        needs.append(
                            Need("instructor_unavailable", i, slot, COSTS["instructor_unavailable"])
                        )
                for g in groups:
                    if slot in p.groups[g].unavailable:
                        needs.append(
                            Need("students_unavailable", g, slot, COSTS["students_unavailable"])
                        )
                if slot in activity.unavailable:
                    needs.append(
                        Need(
                            "activity_unavailable",
                            activity.index,
                            slot,
                            COSTS["activity_unavailable"],
                        )
                    )
                for index, slots in rules:
                    if slot in slots:
                        needs.append(Need("slot_rule", index, slot, COSTS["slot_rule"]))
            if session.fixed_slot is not None and start != session.fixed_slot:
                needs.append(Need("fixed_moved", session.index, None, COSTS["fixed_moved"]))
            result[start] = tuple(needs)
    return result


def _room_needs(
    context: Context, session: Session, domain: SessionDomain
) -> dict[int, tuple[Need, ...]]:
    p = context.problem
    activity = p.activities[session.activity]
    if activity.online:
        return {}
    result: dict[int, tuple[Need, ...]] = dict.fromkeys(domain.rooms, ())
    relaxed: list[tuple[int, int, int, tuple[Need, ...]]] = []
    for room in p.rooms:
        if room.index in result:
            continue
        if room.index in domain.compatible_rooms:
            needs: tuple[Need, ...] = (
                Need("oversized_room", room.index, None, COSTS["oversized_room"]),
            )
        else:
            if room.capacity * 2 < activity.min_capacity:
                continue  # far too small to be a plausible change
            needs = _room_incompatibilities(p, session, room.index)
        cost = sum(need.cost for need in needs)
        relaxed.append((cost, abs(room.capacity - activity.min_capacity), room.index, needs))
    for _, _, room_index, needs in sorted(relaxed)[:MAX_RELAXED_ROOMS]:
        result[room_index] = needs
    return result


def _room_incompatibilities(p: Problem, session: Session, r: int) -> tuple[Need, ...]:
    activity = p.activities[session.activity]
    room = p.rooms[r]
    needs: list[Need] = []
    if session.fixed_room is not None and r != session.fixed_room:
        needs.append(Need("fixed_moved", session.index, None, COSTS["fixed_moved"]))
    if activity.room_type_id and room.type_id != activity.room_type_id:
        needs.append(Need("room_type", r, None, COSTS["room_type"]))
    if not activity.features <= room.features:
        needs.append(Need("room_features", r, None, COSTS["room_features"]))
    if room.capacity < activity.min_capacity:
        shortfall = activity.min_capacity - room.capacity
        needs.append(Need("room_capacity", r, None, COSTS["room_capacity"] * shortfall))
    if (activity.campus is not None and room.campus != activity.campus) or (
        activity.building_id and room.building_id != activity.building_id
    ):
        needs.append(Need("room_location", r, None, COSTS["room_location"]))
    if activity.allowed_rooms and r not in activity.allowed_rooms:
        needs.append(Need("room_not_allowed", r, None, COSTS["room_not_allowed"]))
    return tuple(needs)


ROOM_KINDS = frozenset(
    {
        "room_type",
        "room_features",
        "room_capacity",
        "room_location",
        "room_not_allowed",
        "oversized_room",
    }
)


class Relaxation:
    def __init__(
        self,
        context: Context,
        settings: SolveSettings,
        *,
        hint: dict[int, Placement] | None = None,
        on_progress: Callable[[ProgressEvent], None] | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        self.context = context
        self.settings = settings
        self.hint = hint
        self.runner = Runner(settings, on_progress, should_stop)

    def run(self) -> RelaxationResult:
        runner = self.runner
        p = self.context.problem
        relaxed = relaxed_domains(self.context)
        builder = ScheduleModel(relaxed.context, relaxed=True)
        runner.event("model_built")
        placements = dict(
            self.hint if self.hint is not None else construct(self.context, self.settings.seed)
        )
        total = self.settings.time_limit_seconds
        phases: list[TierOutcome] = []

        unscheduled = builder.objective(UNSCHEDULED)
        if unscheduled is not None and not isinstance(unscheduled, int):
            first = runner.solve(
                builder, unscheduled, placements, total * FIRST_PHASE_SHARE, "unscheduled", None, 0
            )
            phases.append(first.outcome)
            placements = first.placements
            if first.outcome.value is not None:
                builder.model.add(unscheduled <= first.outcome.value)

        measure: dict[str, LinearExpr] = {}
        for rule in p.rules:
            if rule.enforcement == "hard" and rule.type not in SLOT_RULES:
                units = builder.rule_units(rule)
                if units is not None and not isinstance(units, int):
                    measure[f"rule:{rule.id}"] = units
        for activity in p.activities:
            if activity.different_days:
                excess = builder.same_day_excess(activity)
                if excess is not None and not isinstance(excess, int):
                    measure[f"days:{activity.index}"] = excess
        cost = self._cost(builder, relaxed, measure)
        measured: dict[str, int] | None = None
        if cost is not None and not runner.stop_requested():
            second = runner.solve(
                builder,
                cost,
                placements,
                max(0.5, total - runner.spent()),
                "relaxations",
                None,
                1,
                measure,
            )
            phases.append(second.outcome)
            if second.outcome.value is not None:
                placements = second.placements
                measured = second.measured
        if measured is None:
            # No second phase, or it found nothing: price the timetable in hand.
            measured = builder.measure(placements, measure) or {}
        changes = _changes(p, relaxed, placements, measured)
        unplaced = [s.index for s in p.sessions if s.index not in placements]
        return RelaxationResult(
            complete=not unplaced,
            unscheduled=unplaced,
            total_cost=sum(change.cost for change in changes),
            changes=changes,
            placements=placements,
            phases=phases,
            cancelled=runner.cancelled,
            warnings=runner.warnings,
            log_tail=list(runner.log),
        )

    @staticmethod
    def _cost(
        builder: ScheduleModel, relaxed: RelaxedDomains, measure: dict[str, LinearExpr]
    ) -> LinearExpr | None:
        terms: list[LinearExpr] = []
        for s, (x, y) in enumerate(zip(builder.x, builder.y, strict=True)):
            for t, lit in x.items():
                cost = sum(need.cost for need in relaxed.start_needs[s][t])
                if cost:
                    terms.append(cost * lit)
            for r, lit in y.items():
                cost = sum(need.cost for need in relaxed.room_needs[s][r])
                if cost:
                    terms.append(cost * lit)
        for key, expr in measure.items():
            terms.append(
                (COSTS["rule"] if key.startswith("rule:") else COSTS["different_days"]) * expr
            )
        return sum(terms) if terms else None


def _changes(
    p: Problem,
    relaxed: RelaxedDomains,
    placements: dict[int, Placement],
    measured: dict[str, int],
) -> list[Change]:
    grouped: dict[tuple[str, int | None, int | None], Change] = {}
    for s, placement in sorted(placements.items()):
        needs = list(relaxed.start_needs[s].get(placement.slot, ()))
        if placement.room is not None:
            needs += relaxed.room_needs[s].get(placement.room, ())
        for need in needs:
            if need.kind in ROOM_KINDS:
                key: tuple[str, int | None, int | None] = (need.kind, s, need.subject)
            elif need.kind == "slot_closed":
                key = (need.kind, need.slot, None)
            else:
                key = (need.kind, need.subject, None)
            change = grouped.setdefault(key, Change(need.kind, 0, subject=need.subject))
            change.cost += need.cost
            if s not in change.sessions:
                change.sessions.append(s)
            if need.slot is not None and need.slot not in change.slots:
                change.slots.append(need.slot)
    changes = list(grouped.values())
    for rule_index, rule in enumerate(p.rules):
        units = measured.get(f"rule:{rule.id}", 0)
        if units:
            changes.append(Change("rule", COSTS["rule"] * units, subject=rule_index, units=units))
    for activity in p.activities:
        units = measured.get(f"days:{activity.index}", 0)
        if units:
            days = [p.day_of(placements[s].slot) for s in activity.sessions if s in placements]
            crowded = {day for day in days if days.count(day) > 1}
            changes.append(
                Change(
                    "different_days",
                    COSTS["different_days"] * units,
                    sessions=[
                        s
                        for s in activity.sessions
                        if s in placements and p.day_of(placements[s].slot) in crowded
                    ],
                    subject=activity.index,
                    units=units,
                )
            )
    unplaced = [s.index for s in p.sessions if s.index not in placements]
    if unplaced:
        changes.append(Change("unscheduled", 0, sessions=unplaced, units=len(unplaced)))
    for change in changes:
        change.slots.sort()
        change.message = describe(p, change, placements)
    changes.sort(key=lambda c: (c.kind == "unscheduled", -c.cost, c.kind, c.subject or 0))
    return changes


def describe(p: Problem, change: Change, placements: dict[int, Placement]) -> str:
    """An English sentence for a change; interfaces build localized text from the fields."""
    slots = ", ".join(p.slot_label(u) for u in change.slots)
    named = [p.describe_session(p.sessions[s]) for s in change.sessions]
    who = "; ".join(named[:3]) + (f" and {len(named) - 3} more" if len(named) > 3 else "")
    kind, subject = change.kind, change.subject
    session = named[0] if named else ""
    room = ""
    if kind in ROOM_KINDS and change.sessions:
        placed = placements.get(change.sessions[0])
        if placed is not None and placed.room is not None:
            room = p.rooms[placed.room].code
    if kind == "slot_closed":
        return f"Open {slots} for teaching (needed by {who})."
    if kind == "instructor_unavailable" and subject is not None:
        return f"{p.instructors[subject].name} would need to be available at {slots} ({who})."
    if kind == "students_unavailable" and subject is not None:
        return (
            f"Students of {p.groups[subject].code} would need to be available at {slots} ({who})."
        )
    if kind == "activity_unavailable" and subject is not None:
        return f"{p.activities[subject].title} would need to be allowed at {slots}."
    if kind == "slot_rule" and subject is not None:
        return f"Rule '{p.rules[subject].name}' would need to allow {slots} ({who})."
    if kind == "fixed_moved":
        return f"{session} would leave its fixed placement."
    if kind == "room_type":
        return f"{session} would use {room}, which is not of the required room type."
    if kind == "room_features":
        return f"{session} would use {room}, which lacks a required feature."
    if kind == "room_capacity":
        seats = change.cost // COSTS["room_capacity"]
        return f"{session} would use {room}, {seats} seat(s) short."
    if kind == "room_location":
        return f"{session} would use {room}, outside its required campus or building."
    if kind == "room_not_allowed":
        return f"{session} would use {room}, which is not among its allowed rooms."
    if kind == "oversized_room":
        ratio = p.snapshot.term.room_capacity_ratio
        return (
            f"{session} would use {room}, more than {ratio:g} times the seats it needs; raise "
            "the term's room size ratio to let the solver consider it."
        )
    if kind == "different_days" and subject is not None:
        return (
            f"{p.activities[subject].title}: {change.units} more occurrence(s) on a day that "
            "already has one."
        )
    if kind == "rule" and subject is not None:
        return f"Rule '{p.rules[subject].name}' would be broken {change.units} time(s)."
    if kind == "unscheduled":
        return (
            f"{change.units} session(s) cannot be placed even with every relaxation, because "
            f"their instructors, students or rooms have no time left: {who}."
        )
    raise ValueError(f"unknown change kind {kind}")
