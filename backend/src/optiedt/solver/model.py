"""The CP-SAT model (ADR 0005, docs/design/optimization-model.md).

Time is one boolean per session and feasible start; conflicts between sessions of one
instructor or one kind of student are at-most-one constraints per slot; rooms are optional
intervals with one no-overlap per room. Objective terms and soft rules are built on demand,
only for what a tier actually asks for.

Every auxiliary variable is defined exactly, never only bounded from the side the objective
pushes it. Any feasible solution, optimal or not, therefore carries its true objective
values, and the bound a finished tier leaves behind constrains the true value (ADR 0006).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from ortools.sat.python import cp_model

from optiedt.problem.catalog import STABILITY_ROOM_WEIGHT, STABILITY_TIME_WEIGHT, UNSCHEDULED
from optiedt.problem.model import Activity
from optiedt.problem.snapshot import SRule
from optiedt.problem.solution import ObjectiveConfig, Placement
from optiedt.solver.domains import Context

LinearExpr = cp_model.LinearExpr | int
BoolVar = cp_model.IntVar
PAIR_RULES = frozenset({"precedence", "consecutive"})
RESOURCE_RULES = frozenset(
    {
        "max_periods_per_day",
        "max_consecutive_periods",
        "max_days_per_week",
        "break_in_window",
        "avoid_slots",
        "earliest_start",
        "latest_end",
        "campus_travel",
    }
)
SLOT_RULES = frozenset({"avoid_slots", "earliest_start", "latest_end"})


@dataclass(frozen=True, slots=True)
class Resource:
    """Sessions sharing one timetable (an instructor or a kind of student), and how many
    times its contribution counts (atoms with identical sessions are merged).

    At most one of the sessions occupies any slot, so a sum of their covering literals
    at one slot is 0 or 1."""

    sessions: tuple[int, ...]
    multiplicity: int = 1


class PinError(ValueError):
    """A pinned placement is no longer valid for the data being solved."""


class ScheduleModel:
    def __init__(
        self,
        context: Context,
        *,
        pins: dict[int, Placement] | None = None,
        reference: dict[int, Placement] | None = None,
        relaxed: bool = False,
    ) -> None:
        """``relaxed`` leaves hard rules and the different-days requirement unposted, for a
        diagnosis that prices breaking them instead (``solver.relaxation``)."""
        self.context = context
        self.p = context.problem
        self.pins = pins or {}
        self.reference = reference
        self.relaxed = relaxed
        self.model = cp_model.CpModel()
        self.starts: list[tuple[int, ...]] = []
        self.rooms: list[tuple[int, ...]] = []
        self.x: list[dict[int, BoolVar]] = []
        self.y: list[dict[int, BoolVar]] = []
        self.present: list[BoolVar | None] = []
        """None for a session that cannot be placed at all."""
        self.start: list[cp_model.IntVar | None] = []
        self.covering: list[dict[int, list[BoolVar]]] = []
        self.symmetry_groups: list[list[int]] = []
        self._cache: dict[tuple[str, str], LinearExpr | None] = {}
        self._day_used: dict[tuple[tuple[int, ...], int], BoolVar | None] = {}
        self._in_campus: dict[tuple[int, int, int], BoolVar] = {}
        self.instructor_resources = [
            Resource(tuple(s.index for s in self.p.sessions if i.index in s.instructors))
            for i in self.p.instructors
        ]
        self.student_resources = self._student_resources()
        self._variables()
        self._structural()
        self._hard_rules()

    # ── structure ─────────────────────────────────────────────────────

    def _student_resources(self) -> list[Resource]:
        counts: Counter[tuple[int, ...]] = Counter(
            tuple(sessions) for sessions in self.context.atom_sessions if sessions
        )
        return [Resource(sessions, multiplicity) for sessions, multiplicity in counts.items()]

    def _conflict_sets(self) -> list[tuple[int, ...]]:
        """Instructor and student session sets, dropping any set contained in another."""
        sets = {r.sessions for r in self.instructor_resources if len(r.sessions) > 1}
        sets |= {r.sessions for r in self.student_resources if len(r.sessions) > 1}
        ordered = sorted(sets, key=len, reverse=True)
        kept: list[frozenset[int]] = []
        result = []
        for candidate in ordered:
            members = frozenset(candidate)
            if any(members <= other for other in kept):
                continue
            kept.append(members)
            result.append(candidate)
        return result

    def _variables(self) -> None:
        m, p = self.model, self.p
        pinned_sessions = set(self.pins)
        # Rooms the reference timetable uses stay available to the whole activity, even ones
        # the search would otherwise skip as far too large (keeping occurrences interchangeable).
        reference_rooms: dict[int, set[int]] = defaultdict(set)
        for s, placement in (self.reference or {}).items():
            if placement.room is not None and 0 <= s < len(p.sessions):
                reference_rooms[p.sessions[s].activity].add(placement.room)
        for session, domain in zip(p.sessions, self.context.domains, strict=True):
            s = session.index
            starts: Sequence[int] = domain.starts
            rooms: Sequence[int] = domain.rooms
            extra = sorted(
                r
                for r in reference_rooms.get(session.activity, ())
                if r in domain.compatible_rooms and r not in domain.rooms
            )
            if extra:
                rooms = (*domain.rooms, *extra)
            pin = self.pins.get(s)
            if pin is not None:
                if pin.slot not in domain.starts:
                    raise PinError(
                        f"{p.describe_session(session)} cannot stay at {p.slot_label(pin.slot)}."
                    )
                starts = (pin.slot,)
                if pin.room is not None:
                    if pin.room not in domain.compatible_rooms:
                        room = p.rooms[pin.room].code
                        raise PinError(f"{p.describe_session(session)} cannot stay in {room}.")
                    rooms = (pin.room,)
            online = p.activities[session.activity].online
            placeable = bool(starts) and (online or bool(rooms))
            self.starts.append(tuple(starts) if placeable else ())
            self.rooms.append(tuple(rooms) if placeable and not online else ())
            if not placeable:
                if pin is not None:
                    raise PinError(f"{p.describe_session(session)} has no room it may use.")
                self.x.append({})
                self.y.append({})
                self.present.append(None)
                self.start.append(None)
                self.covering.append({})
                continue
            x = {t: m.new_bool_var(f"x{s}_{t}") for t in starts}
            present = m.new_bool_var(f"p{s}")
            m.add(sum(x.values()) == present)
            start = m.new_int_var_from_domain(cp_model.Domain.from_values(starts), f"st{s}")
            m.add(start == sum(t * lit for t, lit in x.items())).only_enforce_if(present)
            y = {r: m.new_bool_var(f"y{s}_{r}") for r in self.rooms[s]}
            if not online:
                m.add(sum(y.values()) == present)
            covering: dict[int, list[BoolVar]] = defaultdict(list)
            for t, lit in x.items():
                for u in range(t, t + session.duration):
                    covering[u].append(lit)
            self.x.append(x)
            self.y.append(y)
            self.present.append(present)
            self.start.append(start)
            self.covering.append(dict(covering))

        by_activity: dict[int, list[int]] = defaultdict(list)
        pair_activities = {
            self.p.activity_index[a]
            for rule in self.p.rules
            if rule.type in PAIR_RULES
            for a in rule.activity_ids
            if a in self.p.activity_index
        }
        for session in p.sessions:
            if (
                session.index not in pinned_sessions
                and session.fixed_slot is None
                and session.fixed_room is None
                and session.activity not in pair_activities
                and self.starts[session.index]
            ):
                by_activity[session.activity].append(session.index)
        self.symmetry_groups = [group for group in by_activity.values() if len(group) > 1]

    def _structural(self) -> None:
        m, p = self.model, self.p
        for members in self._conflict_sets():
            for slot in range(p.n_slots):
                literals = [lit for s in members for lit in self.covering[s].get(slot, ())]
                if len(literals) > 1:
                    m.add_at_most_one(literals)

        room_intervals: dict[int, list[cp_model.IntervalVar]] = defaultdict(list)
        for session in p.sessions:
            s = session.index
            start = self.start[s]
            if start is None:
                continue
            for r, lit in self.y[s].items():
                room_intervals[r].append(
                    m.new_optional_fixed_size_interval_var(
                        start, session.duration, lit, f"iv{s}_{r}"
                    )
                )
        for r, intervals in room_intervals.items():
            blocked = sorted(self.p.rooms[r].unavailable)
            for first, length in _runs(blocked):
                intervals.append(m.new_fixed_size_interval_var(first, length, f"blk{r}_{first}"))
            if len(intervals) > 1:
                m.add_no_overlap(intervals)

        for activity in p.activities:
            if not activity.different_days or self.relaxed:
                continue
            for day in range(p.n_days):
                literals = self._on_day(activity.sessions, day)
                if len(literals) > 1:
                    m.add_at_most_one(literals)

        for group in self.symmetry_groups:
            for earlier, later in pairwise(group):
                present_earlier, present_later = self._placed(earlier), self._placed(later)
                m.add_implication(present_later, present_earlier)
                m.add(_var(self.start[earlier]) < _var(self.start[later])).only_enforce_if(
                    present_later
                )

    def _hard_rules(self) -> None:
        if self.relaxed:
            return
        for rule in self.p.rules:
            if rule.enforcement != "hard" or rule.type in SLOT_RULES:
                continue  # hard slot rules are already part of every domain
            self._rule(rule, hard=True)

    def same_day_excess(self, activity: Activity) -> LinearExpr | None:
        """Occurrences of the activity beyond the first on each day."""
        terms: list[LinearExpr] = []
        for day in range(self.p.n_days):
            literals = self._on_day(activity.sessions, day)
            if len(literals) > 1:
                upper = min(len(literals), len(activity.sessions))
                terms.append(self._excess(sum(literals), 1, upper, "sde"))
        return sum(terms) if terms else None

    # ── building blocks ───────────────────────────────────────────────

    def _placed(self, s: int) -> BoolVar:
        present = self.present[s]
        if present is None:
            raise ValueError(f"session {s} cannot be placed")
        return present

    def occupancy(self, sessions: Iterable[int], slot: int) -> list[BoolVar]:
        """Start literals of ``sessions`` that would occupy ``slot``."""
        return [lit for s in sessions for lit in self.covering[s].get(slot, ())]

    def _on_day(self, sessions: Iterable[int], day: int) -> list[BoolVar]:
        """Start literals of ``sessions`` on ``day`` (a session never spans two days)."""
        p = self.p
        return [lit for s in sessions for t, lit in self.x[s].items() if p.day_of(t) == day]

    def _or(self, literals: Sequence[BoolVar], name: str) -> BoolVar | None:
        """A boolean equal to the disjunction of ``literals``; None when there are none."""
        distinct = list({lit.index: lit for lit in literals}.values())
        if not distinct:
            return None
        if len(distinct) == 1:
            return distinct[0]
        flag = self.model.new_bool_var(name)
        for lit in distinct:
            self.model.add_implication(lit, flag)
        self.model.add_bool_or(distinct).only_enforce_if(flag)
        return flag

    def _and(self, a: LinearExpr, b: LinearExpr, name: str) -> BoolVar:
        """A boolean equal to ``a ∧ b`` for expressions that only take the values 0 and 1."""
        m = self.model
        both = m.new_bool_var(name)
        m.add(both <= a)
        m.add(both <= b)
        m.add(both >= a + b - 1)
        return both

    def _excess(self, total: LinearExpr, limit: int, upper: int, name: str) -> cp_model.IntVar:
        """An integer equal to max(0, total - limit), where total never exceeds ``upper``."""
        excess = self.model.new_int_var(0, max(0, upper - limit), name)
        self.model.add_max_equality(excess, [0, total - limit])
        return excess

    def _least(self, values: Sequence[LinearExpr], upper: int, name: str) -> cp_model.IntVar:
        """An integer equal to the smallest of ``values``, which are between 0 and ``upper``."""
        least = self.model.new_int_var(0, upper, name)
        self.model.add_min_equality(least, values)
        return least

    def _capped(self, literals: Sequence[BoolVar], limit: int, name: str) -> LinearExpr:
        """min(limit, number of true literals)."""
        if len(literals) <= limit:
            return sum(literals)
        return self._least([limit, sum(literals)], limit, name)

    def _day_flag(self, sessions: tuple[int, ...], day: int) -> BoolVar | None:
        """Whether any of ``sessions`` takes place on ``day``; None when none can."""
        key = (sessions, day)
        if key not in self._day_used:
            self._day_used[key] = self._or(self._on_day(sessions, day), f"day{day}")
        return self._day_used[key]

    def _idle(self, resource: Resource) -> list[LinearExpr]:
        """Free open slots between a resource's first and last session of each day.

        ``before[j]`` is true when something occupies slot j or an earlier one, ``after[j]``
        when something occupies slot j or a later one; slot j is idle when it is free,
        something came before it and something comes after it.
        """
        m, p = self.model, self.p
        terms: list[LinearExpr] = []
        for day in range(p.n_days):
            slots = [u for u in p.day_slots(day) if u in p.open_slots]
            occupancy = [self.occupancy(resource.sessions, u) for u in slots]
            possible = [j for j, literals in enumerate(occupancy) if literals]
            if len(possible) < 2 or possible[-1] - possible[0] < 2:
                continue
            occupancy = occupancy[possible[0] : possible[-1] + 1]
            n = len(occupancy)
            before: list[LinearExpr] = []
            for j, literals in enumerate(occupancy):
                if not literals:
                    before.append(before[-1])
                    continue
                if j == 0:
                    before.append(sum(literals))
                    continue
                flag = m.new_bool_var("bf")
                m.add(flag >= sum(literals))
                m.add(flag >= before[-1])
                m.add(flag <= before[-1] + sum(literals))
                before.append(flag)
            after: list[LinearExpr] = [0] * n
            for j in range(n - 1, -1, -1):
                literals = occupancy[j]
                if not literals:
                    after[j] = after[j + 1]
                    continue
                if j == n - 1:
                    after[j] = sum(literals)
                    continue
                flag = m.new_bool_var("af")
                m.add(flag >= sum(literals))
                m.add(flag >= after[j + 1])
                m.add(flag <= after[j + 1] + sum(literals))
                after[j] = flag
            for j in range(1, n - 1):
                busy = sum(occupancy[j])
                idle = m.new_bool_var("idle")
                m.add(idle <= before[j - 1])
                m.add(idle <= after[j + 1])
                m.add(idle + busy <= 1)
                m.add(idle >= before[j - 1] + after[j + 1] - busy - 1)
                terms.append(idle)
        if resource.multiplicity > 1:
            return [resource.multiplicity * term for term in terms]
        return terms

    # ── objectives ────────────────────────────────────────────────────

    def objective(self, code: str) -> LinearExpr | None:
        key = ("objective", code)
        if key not in self._cache:
            self._cache[key] = self._build_objective(code)
        return self._cache[key]

    def _build_objective(self, code: str) -> LinearExpr | None:
        p = self.p
        terms: list[LinearExpr] = []
        if code == UNSCHEDULED:
            constant = 0
            for session in p.sessions:
                present = self.present[session.index]
                if present is None:
                    constant += session.duration
                else:
                    terms.append(session.duration * (1 - present))
            return sum(terms) + constant if terms or constant else None
        if code == "student_idle":
            for resource in self.student_resources:
                terms += self._idle(resource)
        elif code == "instructor_idle":
            for resource in self.instructor_resources:
                terms += self._idle(resource)
        elif code in ("instructor_undesirable", "instructor_preferred"):
            for instructor, resource in zip(p.instructors, self.instructor_resources, strict=True):
                if code == "instructor_undesirable":
                    slots = instructor.undesirable
                elif instructor.preferred:
                    slots = frozenset(range(p.n_slots)) - instructor.preferred
                else:
                    continue
                for slot in slots:
                    terms += self.occupancy(resource.sessions, slot)
        elif code == "instructor_days":
            for instructor, resource in zip(p.instructors, self.instructor_resources, strict=True):
                minimum = math.ceil(p.instructor_load.get(instructor.index, 0) / p.n_periods)
                days = [
                    flag
                    for day in range(p.n_days)
                    if (flag := self._day_flag(resource.sessions, day)) is not None
                ]
                if len(days) > minimum:
                    terms.append(
                        self._excess(sum(days), minimum, len(days), f"xdays{instructor.index}")
                    )
        elif code == "undesirable_slots":
            for session in p.sessions:
                for t, lit in self.x[session.index].items():
                    weight = sum(p.penalty.get(u, 0) for u in range(t, t + session.duration))
                    if weight:
                        terms.append(weight * lit)
        elif code == "room_fit":
            for session in p.sessions:
                need = p.activities[session.activity].min_capacity
                for r, lit in self.y[session.index].items():
                    waste = session.duration * max(0, p.rooms[r].capacity - need)
                    if waste:
                        terms.append(waste * lit)
        elif code == "room_preferences":
            for session in p.sessions:
                activity = p.activities[session.activity]
                for r, lit in self.y[session.index].items():
                    cost = int(bool(activity.preferred_rooms) and r not in activity.preferred_rooms)
                    cost += int(r in activity.avoided_rooms)
                    if cost:
                        terms.append(cost * lit)
        elif code in ("room_stability", "start_consistency"):
            for activity in p.activities:
                term = self._distinct_values(activity, code)
                if term is not None:
                    terms.append(term)
        elif code == "stability":
            if self.reference is None:
                return None
            for activity in p.activities:
                terms += self._stability(activity, self.reference)
        else:
            raise ValueError(f"unknown objective {code}")
        return sum(terms) if terms else None

    def _distinct_values(self, activity: Activity, code: str) -> LinearExpr | None:
        """Distinct rooms (or start periods) used by an activity's sessions, minus one."""
        p = self.p
        sessions = [s for s in activity.sessions if self.x[s]]
        if len(sessions) < 2 or (code == "room_stability" and activity.online):
            return None
        by_value: dict[int, list[BoolVar]] = defaultdict(list)
        for s in sessions:
            if code == "room_stability":
                for r, lit in self.y[s].items():
                    by_value[r].append(lit)
            else:
                for t, lit in self.x[s].items():
                    by_value[p.period_of(t)].append(lit)
        if len(by_value) < 2:
            return None
        used = [self._or(literals, f"{code[:5]}{activity.index}") for literals in by_value.values()]
        any_placed = self._or([self._placed(s) for s in sessions], f"any{activity.index}")
        if any_placed is None:
            return None
        return sum(flag for flag in used if flag is not None) - any_placed

    def _stability(self, activity: Activity, reference: dict[int, Placement]) -> list[LinearExpr]:
        """Reference starts and rooms of the activity that are no longer used (multisets)."""
        ref = [reference[s] for s in activity.sessions if s in reference]
        if not ref:
            return []
        terms: list[LinearExpr] = []
        kept_starts = [
            self._capped(
                [self.x[s][slot] for s in activity.sessions if slot in self.x[s]], count, "kts"
            )
            for slot, count in Counter(pl.slot for pl in ref).items()
        ]
        terms.append(STABILITY_TIME_WEIGHT * (len(ref) - sum(kept_starts)))
        ref_rooms = Counter(pl.room for pl in ref if pl.room is not None)
        if ref_rooms:
            kept_rooms = [
                self._capped(
                    [self.y[s][room] for s in activity.sessions if room in self.y[s]], count, "ktr"
                )
                for room, count in ref_rooms.items()
            ]
            terms.append(STABILITY_ROOM_WEIGHT * (sum(ref_rooms.values()) - sum(kept_rooms)))
        return terms

    # ── rules ─────────────────────────────────────────────────────────

    def rule_units(self, rule: SRule) -> LinearExpr | None:
        key = ("rule", rule.id)
        if key not in self._cache:
            self._cache[key] = self._rule(rule, hard=False)
        return self._cache[key]

    def _rule_resources(self, rule: SRule) -> list[Resource]:
        resources = [
            self.instructor_resources[self.p.instructor_index[i]]
            for i in rule.instructor_ids
            if i in self.p.instructor_index
        ]
        target_groups = {self.p.group_index[g] for g in rule.group_ids if g in self.p.group_index}
        if target_groups:
            counts: Counter[tuple[int, ...]] = Counter()
            for atom, sessions in zip(self.context.atoms, self.context.atom_sessions, strict=True):
                if atom.groups & target_groups and sessions:
                    counts[tuple(sessions)] += 1
            resources += [Resource(sessions, n) for sessions, n in counts.items()]
        return resources

    def _rule(self, rule: SRule, *, hard: bool) -> LinearExpr | None:
        terms: list[LinearExpr] = []
        if rule.type in RESOURCE_RULES:
            for resource in self._rule_resources(rule):
                unit = self._resource_rule(rule, resource, hard)
                if unit is not None:
                    terms.append(
                        unit * resource.multiplicity if resource.multiplicity > 1 else unit
                    )
        if rule.type not in RESOURCE_RULES or (rule.type in SLOT_RULES and rule.activity_ids):
            unit = self._activity_rule(rule, hard)
            if unit is not None:
                terms.append(unit)
        return sum(terms) if terms else None

    def _resource_rule(self, rule: SRule, resource: Resource, hard: bool) -> LinearExpr | None:
        m, p = self.model, self.p
        params = rule.params
        terms: list[LinearExpr] = []

        def cap(literals: Sequence[BoolVar], limit: int, upper: int, label: str) -> None:
            """At most ``limit`` of ``literals`` (of which at most ``upper`` can be true)."""
            upper = min(upper, len(literals))
            if upper <= limit:
                return
            if hard:
                m.add(sum(literals) <= limit)
            else:
                terms.append(self._excess(sum(literals), limit, upper, label))

        if rule.type == "max_periods_per_day":
            limit = int(params["limit"])
            for day in range(p.n_days):
                day_slots = p.day_slots(day)
                literals = [lit for u in day_slots for lit in self.occupancy(resource.sessions, u)]
                cap(literals, limit, len(day_slots), "mpd")
        elif rule.type == "max_consecutive_periods":
            limit = int(params["limit"])
            for day in range(p.n_days):
                for segment in _segments(p.joins_next):
                    joined = [p.slot(day, period) for period in segment]
                    for first in range(len(joined) - limit):
                        window = joined[first : first + limit + 1]
                        literals = [
                            lit for u in window for lit in self.occupancy(resource.sessions, u)
                        ]
                        cap(literals, limit, len(window), "mcp")
        elif rule.type == "max_days_per_week":
            days = [
                flag
                for day in range(p.n_days)
                if (flag := self._day_flag(resource.sessions, day)) is not None
            ]
            cap(days, int(params["limit"]), len(days), "mdw")
        elif rule.type == "break_in_window":
            periods = [int(x) for x in params["periods"]]
            allowed = len(periods) - int(params["min_free"])
            for day in range(p.n_days):
                literals = [
                    lit
                    for period in periods
                    for lit in self.occupancy(resource.sessions, p.slot(day, period))
                ]
                cap(literals, allowed, len(periods), "brk")
        elif rule.type in SLOT_RULES:
            literals = [
                lit for u in self._rule_slots(rule) for lit in self.occupancy(resource.sessions, u)
            ]
            if hard:
                for lit in literals:
                    m.add(lit == 0)
            elif literals:
                terms.append(sum(literals))
        elif rule.type == "campus_travel":
            terms += self._campus_travel(resource, hard)
        return sum(terms) if terms else None

    def _rule_slots(self, rule: SRule) -> frozenset[int]:
        p = self.p
        if rule.type == "avoid_slots":
            return frozenset(p.slot(int(d), int(q)) for d, q in rule.params.get("slots", []))
        period = int(rule.params["period"])
        periods = range(period) if rule.type == "earliest_start" else range(period + 1, p.n_periods)
        return frozenset(p.slot(d, q) for d in range(p.n_days) for q in periods)

    def _at_campus(self, resource: Resource, slot: int, campus: int) -> list[BoolVar]:
        """Literals, at most one of them true, for the resource being on ``campus`` at ``slot``."""
        p = self.p
        found: list[BoolVar] = []
        for s in resource.sessions:
            in_campus = [lit for r, lit in self.y[s].items() if p.rooms[r].campus == campus]
            if not in_campus:
                continue
            duration = p.sessions[s].duration
            for t in range(slot - duration + 1, slot + 1):
                lit = self.x[s].get(t)
                if lit is None:
                    continue
                if len(in_campus) == len(self.y[s]):
                    found.append(lit)
                    continue
                key = (s, t, campus)
                if key not in self._in_campus:
                    self._in_campus[key] = self._and(lit, sum(in_campus), "cmp")
                found.append(self._in_campus[key])
        return found

    def _campus_travel(self, resource: Resource, hard: bool) -> list[LinearExpr]:
        """Adjacent periods on campuses too far apart for the gap between them."""
        p = self.p
        if p.campus_count < 2:
            return []
        terms: list[LinearExpr] = []
        for slot in range(p.n_slots):
            if p.period_of(slot) + 1 >= p.n_periods:
                continue
            gap = p.minutes_between(slot) or 0
            for a in range(p.campus_count):
                for b in range(p.campus_count):
                    if a == b or p.travel_minutes.get((a, b), 0) <= gap:
                        continue
                    here = self._at_campus(resource, slot, a)
                    there = self._at_campus(resource, slot + 1, b)
                    if not here or not there:
                        continue
                    if hard:
                        self.model.add(sum(here) + sum(there) <= 1)
                    else:
                        terms.append(self._and(sum(here), sum(there), "trv"))
        return terms

    def _activity_rule(self, rule: SRule, hard: bool) -> LinearExpr | None:
        m, p = self.model, self.p
        activities = [
            p.activities[p.activity_index[a]] for a in rule.activity_ids if a in p.activity_index
        ]
        terms: list[LinearExpr] = []
        if not activities:
            return None

        if rule.type in SLOT_RULES:
            slots = self._rule_slots(rule)
            for activity in activities:
                for s in activity.sessions:
                    for t, lit in self.x[s].items():
                        hits = sum(1 for u in range(t, t + p.sessions[s].duration) if u in slots)
                        if not hits:
                            continue
                        if hard:
                            m.add(lit == 0)
                        else:
                            terms.append(hits * lit)
        elif rule.type == "min_days_between":
            gap = int(rule.params["days"])
            for activity in activities:
                sessions = [s for s in activity.sessions if self.x[s]]
                for i, s1 in enumerate(sessions):
                    for s2 in sessions[i + 1 :]:
                        for day in range(p.n_days):
                            here = self._on_day((s1,), day)
                            near = [
                                lit for t, lit in self.x[s2].items() if abs(p.day_of(t) - day) < gap
                            ]
                            if not here or not near:
                                continue
                            if hard:
                                m.add(sum(here) + sum(near) <= 1)
                            else:
                                terms.append(self._and(sum(here), sum(near), "mdb"))
        elif rule.type == "not_overlapping":
            sessions = [s for a in activities for s in a.sessions]
            for slot in range(p.n_slots):
                literals = self.occupancy(sessions, slot)
                if len(literals) < 2:
                    continue
                if hard:
                    m.add_at_most_one(literals)
                else:
                    upper = min(len(literals), len(sessions))
                    terms.append(self._excess(sum(literals), 1, upper, "nov"))
        elif rule.type in ("same_start", "same_day"):
            terms += self._aligned(rule, activities, hard)
        elif rule.type == "different_days":
            for day in range(p.n_days):
                flags = [
                    flag
                    for activity in activities
                    if (flag := self._day_flag(activity.sessions, day)) is not None
                ]
                if len(flags) < 2:
                    continue
                if hard:
                    m.add(sum(flags) <= 1)
                else:
                    terms.append(self._excess(sum(flags), 1, len(flags), "ddx"))
        elif rule.type in PAIR_RULES and len(activities) == 2:
            terms += self._pairs(rule, activities[0], activities[1], hard)
        return sum(terms) if terms else None

    def _aligned(self, rule: SRule, activities: list[Activity], hard: bool) -> list[LinearExpr]:
        """same_start / same_day: occurrences of each other activity matched with the first
        one's, on multisets of start slots (or days)."""
        m, p = self.model, self.p
        by_start = rule.type == "same_start"

        def keyed(activity: Activity) -> dict[int, list[BoolVar]]:
            result: dict[int, list[BoolVar]] = defaultdict(list)
            for s in activity.sessions:
                for t, lit in self.x[s].items():
                    result[t if by_start else p.day_of(t)].append(lit)
            return result

        def placed(activity: Activity) -> list[BoolVar]:
            return [present for s in activity.sessions if (present := self.present[s]) is not None]

        first = activities[0]
        first_keys = keyed(first)
        first_placed = placed(first)
        terms: list[LinearExpr] = []
        for other in activities[1:]:
            other_placed = placed(other)
            upper = min(len(first_placed), len(other_placed))
            if upper == 0:
                continue
            aligned = self._least([sum(first_placed), sum(other_placed)], upper, "aln")
            common: list[LinearExpr] = []
            for key, right in keyed(other).items():
                left = first_keys.get(key)
                if left:
                    bound = min(len(left), len(right), upper)
                    common.append(self._least([sum(left), sum(right)], bound, "cmn"))
            if hard:
                m.add(sum(common) >= aligned)
            else:
                terms.append(aligned - sum(common))
        return terms

    def _pairs(
        self, rule: SRule, first: Activity, second: Activity, hard: bool
    ) -> list[LinearExpr]:
        """precedence / consecutive between occurrence k of each activity."""
        m, p = self.model, self.p
        terms: list[LinearExpr] = []
        for sa, sb in zip(first.sessions, second.sessions, strict=False):
            start_a, start_b = self.start[sa], self.start[sb]
            if start_a is None or start_b is None:
                continue
            pa, pb = self._placed(sa), self._placed(sb)
            if rule.type == "precedence":
                if hard:
                    m.add(start_b >= start_a + first.duration).only_enforce_if([pa, pb])
                    continue
                late = m.new_bool_var("late")
                m.add(start_b >= start_a + first.duration).only_enforce_if([pa, pb, late.Not()])
                m.add_implication(late, pa)
                m.add_implication(late, pb)
                m.add(start_b < start_a + first.duration).only_enforce_if(late)
                terms.append(late)
                continue
            together = self._and(pa, pb, "both")
            matches = [
                self._and(lit, self.x[sb][t + first.duration], "next")
                for t, lit in self.x[sa].items()
                if t + first.duration in self.x[sb] and p.day_of(t + first.duration) == p.day_of(t)
            ]
            if hard:
                m.add(together <= sum(matches))
            else:
                terms.append(together - sum(matches))
        return terms

    # ── tiers, hints, results ─────────────────────────────────────────

    def has_terms(self, config: ObjectiveConfig, tier: int) -> bool:
        """Whether any objective or soft rule is assigned to ``tier`` (without building it)."""
        return any(
            objective_tier == tier for objective_tier, _ in config.objectives.values()
        ) or any(rule.enforcement == "soft" and rule.tier == tier for rule in self.p.rules)

    def tier_expression(self, config: ObjectiveConfig, tier: int) -> LinearExpr | None:
        if tier == 0:
            return self.objective(UNSCHEDULED)
        terms: list[LinearExpr] = []
        for code, (objective_tier, weight) in sorted(config.objectives.items()):
            if objective_tier != tier:
                continue
            expr = self.objective(code)
            if expr is not None:
                terms.append(weight * expr if weight != 1 else expr)
        for rule in self.p.rules:
            if rule.enforcement == "soft" and rule.tier == tier:
                expr = self.rule_units(rule)
                if expr is not None:
                    terms.append(rule.weight * expr if rule.weight != 1 else expr)
        return sum(terms) if terms else None

    def canonical(self, placements: dict[int, Placement]) -> dict[int, Placement]:
        """Reorders interchangeable occurrences by start, as the model's symmetry breaking does."""
        result = dict(placements)
        for group in self.symmetry_groups:
            placed = sorted(
                (result.pop(s) for s in group if s in result),
                key=lambda pl: (pl.slot, pl.room or -1),
            )
            for s, placement in zip(group, placed, strict=False):
                result[s] = placement
        return result

    def assignment(
        self, placements: dict[int, Placement], seconds: float = 10.0
    ) -> tuple[list[int] | None, float]:
        """The value of every model variable in the timetable ``placements``, and the
        deterministic time spent finding it.

        Decisions follow from the placements and every auxiliary variable from the decisions
        (they are exact), so this is a propagation, not a search. Returns None when the
        placements break a constraint of the model.
        """
        solver, dt = self._fixed(placements, seconds)
        if solver is None:
            return None, dt
        return list(solver.response_proto.solution), dt

    def measure(
        self, placements: dict[int, Placement], expressions: dict[str, LinearExpr]
    ) -> dict[str, int] | None:
        """Values of model expressions in the timetable ``placements``."""
        solver, _ = self._fixed(placements, 10.0)
        if solver is None:
            return None
        return {key: int(solver.value(expr)) for key, expr in expressions.items()}

    def _fixed(
        self, placements: dict[int, Placement], seconds: float
    ) -> tuple[cp_model.CpSolver | None, float]:
        model = self.model.clone()
        model.clear_objective()  # type: ignore[no-untyped-call]
        model.clear_hints()  # type: ignore[no-untyped-call]
        fixed = self.canonical(placements)
        for session in self.p.sessions:
            s = session.index
            present = self.present[s]
            if present is None:
                continue
            placement = fixed.get(s)
            if placement is None or placement.slot not in self.x[s]:
                model.add(present == 0)
                continue
            model.add(self.x[s][placement.slot] == 1)
            if placement.room is not None and placement.room in self.y[s]:
                model.add(self.y[s][placement.room] == 1)
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        solver.parameters.max_time_in_seconds = seconds
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None, solver.deterministic_time
        return solver, solver.deterministic_time

    def add_full_hint(self, values: list[int]) -> None:
        """Hints every variable, typically with the previous solution's values."""
        self.model.clear_hints()  # type: ignore[no-untyped-call]
        hint = self.model.proto.solution_hint
        hint.vars.extend(range(len(values)))
        hint.values.extend(values)

    def add_hint(self, placements: dict[int, Placement]) -> None:
        """Hints the decision variables only; the solver has to complete the rest."""
        m = self.model
        m.clear_hints()  # type: ignore[no-untyped-call]
        hint = self.canonical(placements)
        for session in self.p.sessions:
            s = session.index
            present = self.present[s]
            if present is None:
                continue
            placement = hint.get(s)
            slot = placement.slot if placement is not None and placement.slot in self.x[s] else None
            room = placement.room if placement is not None and slot is not None else None
            for t, lit in self.x[s].items():
                m.add_hint(lit, t == slot)
            m.add_hint(present, slot is not None)
            for r, lit in self.y[s].items():
                m.add_hint(lit, r == room)

    def extract(self, solver: cp_model.CpSolver) -> dict[int, Placement]:
        placements: dict[int, Placement] = {}
        for session in self.p.sessions:
            s = session.index
            slot = next((t for t, lit in self.x[s].items() if solver.boolean_value(lit)), None)
            if slot is None:
                continue
            room = next((r for r, lit in self.y[s].items() if solver.boolean_value(lit)), None)
            placements[s] = Placement(slot, room)
        return placements

    def fork(self) -> ScheduleModel:
        """A copy sharing decision variables, with its own constraints and objective terms."""
        clone = object.__new__(ScheduleModel)
        clone.__dict__.update(self.__dict__)
        clone.model = self.model.clone()
        clone._cache = dict(self._cache)
        clone._day_used = dict(self._day_used)
        clone._in_campus = dict(self._in_campus)
        return clone


def _var(value: cp_model.IntVar | None) -> cp_model.IntVar:
    if value is None:
        raise ValueError("expected a variable")
    return value


def _runs(slots: Sequence[int]) -> list[tuple[int, int]]:
    """Consecutive runs in a sorted slot list as (first, length)."""
    runs: list[tuple[int, int]] = []
    for slot in slots:
        if runs and runs[-1][0] + runs[-1][1] == slot:
            runs[-1] = (runs[-1][0], runs[-1][1] + 1)
        else:
            runs.append((slot, 1))
    return runs


def _segments(joins_next: Sequence[bool]) -> list[list[int]]:
    """Periods of a day split where a session may not continue into the next period."""
    segments: list[list[int]] = [[]]
    for period, joins in enumerate(joins_next):
        segments[-1].append(period)
        if not joins:
            segments.append([])
    return [s for s in segments if s]
