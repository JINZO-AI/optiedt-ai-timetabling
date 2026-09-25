"""Independent evaluation of a timetable: hard requirements, objectives and rule violations.

Every metric is a sum of contributions from single resources (an instructor, a kind of
student, a session, an activity), so the effect of moving one session is computed from the
resources it touches. Nothing here imports the solver (ADR 0009).
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from optiedt.evaluation.groups import GroupOverlap
from optiedt.evaluation.types import Evaluation, ObjectiveConfig, Placement, Violation, empty_tiers
from optiedt.problem.atoms import atoms_of_groups, build_atoms
from optiedt.problem.catalog import STABILITY_ROOM_WEIGHT, STABILITY_TIME_WEIGHT, UNSCHEDULED
from optiedt.problem.model import Problem, Session
from optiedt.problem.snapshot import SRule

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
INSTRUCTOR_OBJECTIVES = (
    "instructor_idle",
    "instructor_undesirable",
    "instructor_preferred",
    "instructor_days",
)
SESSION_OBJECTIVES = ("undesirable_slots", "room_fit", "room_preferences")
ACTIVITY_OBJECTIVES = ("room_stability", "start_consistency", "stability")
ALL_OBJECTIVES = (
    UNSCHEDULED,
    "student_idle",
    *INSTRUCTOR_OBJECTIVES,
    *SESSION_OBJECTIVES,
    *ACTIVITY_OBJECTIVES,
)


@dataclass(frozen=True, slots=True)
class MoveResult:
    """Consequences of placing one session somewhere, all other sessions unchanged."""

    violations: list[Violation]
    """Hard problems the session would have in its new place."""
    objective_deltas: dict[str, int]
    rule_deltas: dict[str, int]
    tier_deltas: list[int]

    @property
    def feasible(self) -> bool:
        return not self.violations


@dataclass
class _Occupancy:
    placements: dict[int, Placement]
    instructor: list[dict[int, list[int]]] = field(default_factory=list)
    atom: list[dict[int, list[int]]] = field(default_factory=list)
    room: list[dict[int, list[int]]] = field(default_factory=list)
    by_slot: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))


class Evaluator:
    def __init__(self, problem: Problem, config: ObjectiveConfig) -> None:
        self.p = problem
        self.config = config
        self.overlap = GroupOverlap(problem)
        self.atoms = build_atoms(problem)
        group_atoms = atoms_of_groups(self.atoms, len(problem.groups))
        self.session_atoms = [
            frozenset().union(*(group_atoms[g] for g in s.groups)) for s in problem.sessions
        ]
        self.atom_labels = [
            " / ".join(
                sorted(
                    (problem.groups[g].code for g in a.groups),
                    key=lambda code: (len(code), code),
                )
            )
            for a in self.atoms
        ]
        self.unavailable_groups = [g for g in problem.groups if g.unavailable]
        self.min_days = {
            i: math.ceil(load / problem.n_periods) for i, load in problem.instructor_load.items()
        }
        self.rule_instructors: dict[str, frozenset[int]] = {}
        self.rule_atoms: dict[str, frozenset[int]] = {}
        self.rule_groups: dict[str, tuple[int, ...]] = {}
        self.rule_activities: dict[str, tuple[int, ...]] = {}
        for rule in problem.rules:
            self.rule_instructors[rule.id] = frozenset(
                problem.instructor_index[i]
                for i in rule.instructor_ids
                if i in problem.instructor_index
            )
            groups = tuple(
                problem.group_index[g] for g in rule.group_ids if g in problem.group_index
            )
            self.rule_groups[rule.id] = groups
            self.rule_atoms[rule.id] = frozenset().union(*(group_atoms[g] for g in groups))
            self.rule_activities[rule.id] = tuple(
                problem.activity_index[a] for a in rule.activity_ids if a in problem.activity_index
            )
        self.slot_rules = [r for r in problem.rules if r.type in SLOT_RULES]
        self.rule_slots = {r.id: self._slots_of_rule(r) for r in self.slot_rules}
        self.reference_by_activity: dict[int, tuple[Counter[int], Counter[int]]] = {}
        if config.reference is not None:
            for activity in problem.activities:
                starts: Counter[int] = Counter()
                rooms: Counter[int] = Counter()
                for s in activity.sessions:
                    placed = config.reference.get(s)
                    if placed is not None:
                        starts[placed.slot] += 1
                        if placed.room is not None:
                            rooms[placed.room] += 1
                self.reference_by_activity[activity.index] = (starts, rooms)

    # ── helpers ───────────────────────────────────────────────────────

    def covered(self, session: Session, placement: Placement) -> range:
        return range(placement.slot, placement.slot + session.duration)

    def _slots_of_rule(self, rule: SRule) -> frozenset[int]:
        p = self.p
        if rule.type == "avoid_slots":
            return frozenset(p.slot(int(d), int(q)) for d, q in rule.params.get("slots", []))
        period = int(rule.params["period"])
        periods = range(period) if rule.type == "earliest_start" else range(period + 1, p.n_periods)
        return frozenset(p.slot(d, q) for d in range(p.n_days) for q in periods)

    def _occupancy(self, placements: Mapping[int, Placement]) -> _Occupancy:
        p = self.p
        occupancy = _Occupancy(
            placements=dict(placements),
            instructor=[defaultdict(list) for _ in p.instructors],
            atom=[defaultdict(list) for _ in self.atoms],
            room=[defaultdict(list) for _ in p.rooms],
        )
        for s, placement in placements.items():
            session = p.sessions[s]
            for slot in self.covered(session, placement):
                occupancy.by_slot[slot].append(s)
                for i in session.instructors:
                    occupancy.instructor[i][slot].append(s)
                for a in self.session_atoms[s]:
                    occupancy.atom[a][slot].append(s)
                if placement.room is not None and 0 <= placement.room < len(p.rooms):
                    occupancy.room[placement.room][slot].append(s)
        return occupancy

    def _by_day(self, slots: Iterable[int]) -> dict[int, list[int]]:
        days: dict[int, list[int]] = defaultdict(list)
        for slot in slots:
            days[self.p.day_of(slot)].append(slot)
        return days

    def idle_periods(self, slots: Iterable[int]) -> int:
        total = 0
        occupied = set(slots)
        for day_slots in self._by_day(occupied).values():
            first, last = min(day_slots), max(day_slots)
            total += sum(
                1
                for slot in range(first + 1, last)
                if slot not in occupied and slot in self.p.open_slots
            )
        return total

    # ── hard requirements of one placement ────────────────────────────

    def placement_violations(self, s: int, placement: Placement) -> list[Violation]:
        """Problems of this placement on its own, ignoring every other session."""
        p = self.p
        session = p.sessions[s]
        activity = p.activities[session.activity]
        label = p.describe_session(session)
        found: list[Violation] = []

        def add(
            code: str, message: str, slots: Iterable[int] = (), rule: str | None = None
        ) -> None:
            found.append(Violation(code, f"{label}: {message}", (s,), tuple(slots), rule))

        period = p.period_of(placement.slot)
        if (
            placement.slot < 0
            or placement.slot >= p.n_slots
            or period + session.duration > p.n_periods
        ):
            add("past_last_period", "does not fit in the day.")
            return found
        covered = list(self.covered(session, placement))
        closed = [t for t in covered if t not in p.open_slots]
        if closed:
            add("slot_closed", f"placed in a closed slot ({p.slot_label(closed[0])}).", closed)
        for k in range(session.duration - 1):
            if not p.joins_next[period + k]:
                add("crosses_break", "runs across a break between periods.")
                break
        for i in session.instructors:
            clash = [t for t in covered if t in p.instructors[i].unavailable]
            if clash:
                add(
                    "instructor_unavailable",
                    f"{p.instructors[i].name} is unavailable at {p.slot_label(clash[0])}.",
                    clash,
                )
        for group in self.unavailable_groups:
            if any(self.overlap.share_students(group.index, g) for g in session.groups):
                clash = [t for t in covered if t in group.unavailable]
                if clash:
                    add(
                        "students_unavailable",
                        f"students of {group.code} are unavailable at {p.slot_label(clash[0])}.",
                        clash,
                    )
        clash = [t for t in covered if t in activity.unavailable]
        if clash:
            add("activity_unavailable", f"not allowed at {p.slot_label(clash[0])}.", clash)
        if session.fixed_slot is not None and placement.slot != session.fixed_slot:
            add("fixed_moved", f"is fixed at {p.slot_label(session.fixed_slot)}.")
        for rule in self.slot_rules:
            if rule.enforcement != "hard" or not self._rule_targets_session(rule, session):
                continue
            clash = [t for t in covered if t in self.rule_slots[rule.id]]
            if clash:
                add(
                    f"rule:{rule.type}",
                    f"rule '{rule.name}' keeps {p.slot_label(clash[0])} free.",
                    clash,
                    rule.id,
                )
        found.extend(self._room_violations(s, session, placement, covered, label))
        return found

    def _rule_targets_session(self, rule: SRule, session: Session) -> bool:
        if session.activity in self.rule_activities[rule.id]:
            return True
        if self.rule_instructors[rule.id] & set(session.instructors):
            return True
        return any(
            self.overlap.share_students(g, h)
            for g in self.rule_groups[rule.id]
            for h in session.groups
        )

    def _room_violations(
        self, s: int, session: Session, placement: Placement, covered: list[int], label: str
    ) -> list[Violation]:
        p = self.p
        activity = p.activities[session.activity]
        found: list[Violation] = []

        def add(code: str, message: str, slots: Iterable[int] = ()) -> None:
            found.append(Violation(code, f"{label}: {message}", (s,), tuple(slots)))

        if activity.online:
            if placement.room is not None:
                add("room_for_online", "is delivered online and must not occupy a room.")
            return found
        if placement.room is None:
            add("room_missing", "has no room.")
            return found
        if not 0 <= placement.room < len(p.rooms):
            add("room_missing", "is in a room that no longer exists.")
            return found
        room = p.rooms[placement.room]
        if session.fixed_room is not None and placement.room != session.fixed_room:
            add("fixed_moved", f"is fixed in {p.rooms[session.fixed_room].code}.")
        if activity.room_type_id and room.type_id != activity.room_type_id:
            add("room_type", f"{room.code} is not of the required room type.")
        missing = activity.features - room.features
        if missing:
            add("room_features", f"{room.code} lacks a required feature.")
        if room.capacity < activity.min_capacity:
            add(
                "room_capacity",
                f"{room.code} seats {room.capacity}, {activity.min_capacity} are needed.",
            )
        if activity.campus is not None and room.campus != activity.campus:
            add("campus", f"{room.code} is not on the required campus.")
        if activity.building_id and room.building_id != activity.building_id:
            add("building", f"{room.code} is not in the required building.")
        if activity.allowed_rooms and placement.room not in activity.allowed_rooms:
            add("room_not_allowed", f"{room.code} is not one of the allowed rooms.")
        blocked = [t for t in covered if t in room.unavailable]
        if blocked:
            add(
                "room_unavailable",
                f"{room.code} is unavailable at {p.slot_label(blocked[0])}.",
                blocked,
            )
        return found

    # ── conflicts between sessions ────────────────────────────────────

    def _conflicts(self, occupancy: _Occupancy) -> list[Violation]:
        pairs: dict[tuple[str, int, int], list[int]] = defaultdict(list)
        for slot, sessions in occupancy.by_slot.items():
            if len(sessions) < 2:
                continue
            for index, a in enumerate(sessions):
                for b in sessions[index + 1 :]:
                    for code in self.pair_conflicts(
                        a, occupancy.placements[a], b, occupancy.placements[b]
                    ):
                        pairs[(code, min(a, b), max(a, b))].append(slot)
        return [
            self.conflict_violation(code, a, b, slots, occupancy.placements[a].room)
            for (code, a, b), slots in pairs.items()
        ]

    def pair_conflicts(self, a: int, pa: Placement, b: int, pb: Placement) -> list[str]:
        """Kinds of conflict between two sessions that overlap in time."""
        sa, sb = self.p.sessions[a], self.p.sessions[b]
        codes = []
        if set(sa.instructors) & set(sb.instructors):
            codes.append("instructor_conflict")
        if self.overlap.sessions_share_students(sa.groups, sb.groups):
            codes.append("student_conflict")
        if pa.room is not None and pa.room == pb.room:
            codes.append("room_conflict")
        return codes

    def conflict_violation(
        self, code: str, a: int, b: int, slots: list[int], room: int | None
    ) -> Violation:
        p = self.p
        sa, sb = p.sessions[a], p.sessions[b]
        if code == "instructor_conflict":
            names = ", ".join(
                p.instructors[i].name for i in sorted(set(sa.instructors) & set(sb.instructors))
            )
            detail = f"{names} would teach both"
        elif code == "room_conflict" and room is not None:
            detail = f"{p.rooms[room].code} would host both"
        else:
            detail = "the same students would attend both"
        return Violation(
            code,
            f"{p.describe_session(sa)} and {p.describe_session(sb)} overlap at "
            f"{p.slot_label(min(slots))}: {detail}.",
            (a, b),
            tuple(sorted(slots)),
        )

    def _different_days(self, placements: Mapping[int, Placement]) -> list[Violation]:
        p = self.p
        found = []
        for activity in p.activities:
            if not activity.different_days:
                continue
            by_day: dict[int, list[int]] = defaultdict(list)
            for s in activity.sessions:
                if s in placements:
                    by_day[p.day_of(placements[s].slot)].append(s)
            for day_sessions in by_day.values():
                if len(day_sessions) > 1:
                    found.append(
                        Violation(
                            "same_day_occurrences",
                            f"{activity.title}: {len(day_sessions)} occurrences on the same day, "
                            "they must be on different days.",
                            tuple(sorted(day_sessions)),
                        )
                    )
        return found

    # ── per-resource contributions ────────────────────────────────────

    def instructor_terms(self, i: int, slots: set[int]) -> dict[str, int]:
        instructor = self.p.instructors[i]
        days = len({self.p.day_of(t) for t in slots})
        return {
            "instructor_idle": self.idle_periods(slots),
            "instructor_undesirable": len(slots & instructor.undesirable),
            "instructor_preferred": len(slots - instructor.preferred)
            if instructor.preferred
            else 0,
            "instructor_days": max(0, days - self.min_days.get(i, 0)),
        }

    def session_terms(self, s: int, placement: Placement | None) -> dict[str, int]:
        if placement is None:
            return dict.fromkeys(SESSION_OBJECTIVES, 0)
        p = self.p
        session = p.sessions[s]
        activity = p.activities[session.activity]
        penalty = sum(p.penalty.get(t, 0) for t in self.covered(session, placement))
        fit = preference = 0
        if (
            placement.room is not None
            and 0 <= placement.room < len(p.rooms)
            and not activity.online
        ):
            room = p.rooms[placement.room]
            fit = session.duration * max(0, room.capacity - activity.min_capacity)
            if activity.preferred_rooms and placement.room not in activity.preferred_rooms:
                preference += 1
            if placement.room in activity.avoided_rooms:
                preference += 1
        return {"undesirable_slots": penalty, "room_fit": fit, "room_preferences": preference}

    def activity_terms(self, a: int, placements: Mapping[int, Placement]) -> dict[str, int]:
        p = self.p
        activity = p.activities[a]
        placed = [placements[s] for s in activity.sessions if s in placements]
        rooms = {x.room for x in placed if x.room is not None}
        periods = {p.period_of(x.slot) for x in placed}
        terms = {
            "room_stability": max(0, len(rooms) - 1) if not activity.online else 0,
            "start_consistency": max(0, len(periods) - 1),
            "stability": 0,
        }
        if a in self.reference_by_activity:
            ref_starts, ref_rooms = self.reference_by_activity[a]
            starts = Counter(x.slot for x in placed)
            now_rooms = Counter(x.room for x in placed if x.room is not None)
            time_moves = sum(ref_starts.values()) - sum((ref_starts & starts).values())
            room_moves = sum(ref_rooms.values()) - sum((ref_rooms & now_rooms).values())
            terms["stability"] = (
                STABILITY_TIME_WEIGHT * time_moves + STABILITY_ROOM_WEIGHT * room_moves
            )
        return terms

    # ── rules ─────────────────────────────────────────────────────────

    def resource_rule_units(
        self,
        rule: SRule,
        slots: set[int],
        slot_sessions: Mapping[int, list[int]] | None,
        placements: Mapping[int, Placement],
    ) -> int:
        """Violation units of a per-resource rule for one resource occupying ``slots``."""
        p = self.p
        params = rule.params
        if rule.type == "max_periods_per_day":
            limit = int(params["limit"])
            return sum(max(0, len(day) - limit) for day in self._by_day(slots).values())
        if rule.type == "max_days_per_week":
            return max(0, len({p.day_of(t) for t in slots}) - int(params["limit"]))
        if rule.type == "max_consecutive_periods":
            limit = int(params["limit"])
            units = 0
            for day in range(p.n_days):
                run = 0
                for period in range(p.n_periods):
                    slot = p.slot(day, period)
                    if slot in slots:
                        run += 1
                    else:
                        units += max(0, run - limit)
                        run = 0
                    if not p.joins_next[period] or period == p.n_periods - 1:
                        units += max(0, run - limit)
                        run = 0
            return units
        if rule.type == "break_in_window":
            window = [int(x) for x in params["periods"]]
            need = int(params["min_free"])
            units = 0
            for day in range(p.n_days):
                free = sum(1 for period in window if p.slot(day, period) not in slots)
                units += max(0, need - free)
            return units
        if rule.type in SLOT_RULES:
            return len(slots & self.rule_slots[rule.id])
        if rule.type == "campus_travel":
            if slot_sessions is None:
                return 0
            units = 0
            for slot in sorted(slot_sessions):
                following = slot + 1
                if p.period_of(slot) + 1 >= p.n_periods or following not in slot_sessions:
                    continue
                gap = p.minutes_between(slot) or 0
                for s1 in slot_sessions[slot]:
                    for s2 in slot_sessions[following]:
                        if s1 == s2:
                            continue
                        r1, r2 = placements[s1].room, placements[s2].room
                        if r1 is None or r2 is None:
                            continue
                        c1, c2 = p.rooms[r1].campus, p.rooms[r2].campus
                        if c1 != c2 and p.travel_minutes.get((c1, c2), 0) > gap:
                            units += 1
            return units
        raise ValueError(f"not a resource rule: {rule.type}")

    def activity_rule_units(self, rule: SRule, placements: Mapping[int, Placement]) -> int:
        p = self.p
        activities = [p.activities[a] for a in self.rule_activities[rule.id]]
        if rule.type in SLOT_RULES:
            slots = self.rule_slots[rule.id]
            return sum(
                len(set(self.covered(p.sessions[s], placements[s])) & slots)
                for activity in activities
                for s in activity.sessions
                if s in placements
            )
        if rule.type == "min_days_between":
            days = int(rule.params["days"])
            units = 0
            for activity in activities:
                placed = [
                    p.day_of(placements[s].slot) for s in activity.sessions if s in placements
                ]
                for i, d1 in enumerate(placed):
                    for d2 in placed[i + 1 :]:
                        if abs(d1 - d2) < days:
                            units += 1
            return units
        if rule.type == "not_overlapping":
            counts: Counter[int] = Counter()
            for activity in activities:
                for s in activity.sessions:
                    if s in placements:
                        counts.update(self.covered(p.sessions[s], placements[s]))
            return sum(max(0, c - 1) for c in counts.values())
        if rule.type in ("same_start", "same_day"):

            def key(s: int) -> int:
                slot = placements[s].slot
                return slot if rule.type == "same_start" else p.day_of(slot)

            first = activities[0]
            base = Counter(key(s) for s in first.sessions if s in placements)
            units = 0
            for other in activities[1:]:
                values = Counter(key(s) for s in other.sessions if s in placements)
                alignable = min(sum(base.values()), sum(values.values()))
                units += alignable - sum((base & values).values())
            return units
        if rule.type == "different_days":
            present: dict[int, set[int]] = defaultdict(set)
            for activity in activities:
                for s in activity.sessions:
                    if s in placements:
                        present[p.day_of(placements[s].slot)].add(activity.index)
            return sum(max(0, len(members) - 1) for members in present.values())
        if rule.type in ("precedence", "consecutive"):
            if len(activities) != 2:
                return 0
            first, second = activities
            units = 0
            for sa, sb in zip(first.sessions, second.sessions, strict=False):
                if sa not in placements or sb not in placements:
                    continue
                start_a, start_b = placements[sa].slot, placements[sb].slot
                end_a = start_a + first.duration
                if rule.type == "precedence":
                    units += int(end_a > start_b)
                else:
                    same_day = p.day_of(start_a) == p.day_of(start_b)
                    units += int(not (same_day and start_b == end_a))
            return units
        raise ValueError(f"not an activity rule: {rule.type}")

    def _rule_units(self, rule: SRule, occupancy: _Occupancy) -> int:
        units = 0
        if rule.type in RESOURCE_RULES:
            for i in self.rule_instructors[rule.id]:
                slots = set(occupancy.instructor[i])
                units += self.resource_rule_units(
                    rule, slots, occupancy.instructor[i], occupancy.placements
                )
            for a in self.rule_atoms[rule.id]:
                slots = set(occupancy.atom[a])
                units += self.resource_rule_units(
                    rule, slots, occupancy.atom[a], occupancy.placements
                )
        if rule.type not in RESOURCE_RULES or (
            rule.type in SLOT_RULES and self.rule_activities[rule.id]
        ):
            units += self.activity_rule_units(rule, occupancy.placements)
        return units

    # ── full evaluation ───────────────────────────────────────────────

    def evaluate(self, placements: Mapping[int, Placement]) -> Evaluation:
        p = self.p
        occupancy = self._occupancy(placements)
        unscheduled = [s.index for s in p.sessions if s.index not in placements]

        violations: list[Violation] = []
        for s, placement in placements.items():
            violations.extend(self.placement_violations(s, placement))
        violations.extend(self._conflicts(occupancy))
        violations.extend(self._different_days(placements))

        values: dict[str, int] = dict.fromkeys(ALL_OBJECTIVES, 0)
        values[UNSCHEDULED] = sum(p.sessions[s].duration for s in unscheduled)
        contributors: dict[str, list[tuple[str, int]]] = defaultdict(list)

        for a, slot_map in enumerate(occupancy.atom):
            idle = self.idle_periods(slot_map)
            values["student_idle"] += idle
            if idle:
                contributors["student_idle"].append((self.atom_labels[a], idle))
        for i, slot_map in enumerate(occupancy.instructor):
            for code, value in self.instructor_terms(i, set(slot_map)).items():
                values[code] += value
                if value:
                    contributors[code].append((p.instructors[i].name, value))
        for session in p.sessions:
            for code, value in self.session_terms(
                session.index, placements.get(session.index)
            ).items():
                values[code] += value
                if value:
                    contributors[code].append((p.describe_session(session), value))
        for activity in p.activities:
            for code, value in self.activity_terms(activity.index, placements).items():
                values[code] += value
                if value:
                    contributors[code].append((activity.title, value))

        rule_values: dict[str, int] = {}
        for rule in p.rules:
            units = self._rule_units(rule, occupancy)
            if rule.enforcement == "hard":
                if units:
                    violations.append(
                        Violation(
                            f"rule:{rule.type}",
                            f"Rule '{rule.name}' is broken ({units} violation(s)).",
                            (),
                            rule_id=rule.id,
                        )
                    )
            else:
                rule_values[rule.id] = units

        violations = _dedupe(violations)
        return Evaluation(
            complete=not unscheduled,
            unscheduled=unscheduled,
            violations=violations,
            objective_values=values,
            rule_values=rule_values,
            tiers=self.tiers(values, rule_values),
            contributors={
                code: sorted(items, key=lambda item: -item[1])[:10]
                for code, items in contributors.items()
            },
        )

    def tiers(self, values: Mapping[str, int], rule_values: Mapping[str, int]) -> list[int]:
        tiers = empty_tiers()
        tiers[0] = values.get(UNSCHEDULED, 0)
        for code, (tier, weight) in self.config.objectives.items():
            tiers[tier] += weight * values.get(code, 0)
        for rule in self.p.rules:
            if rule.enforcement == "soft":
                tiers[rule.tier] += rule.weight * rule_values.get(rule.id, 0)
        return tiers

    # ── moving one session ────────────────────────────────────────────

    def move_context(self, placements: Mapping[int, Placement], s: int) -> MoveContext:
        return MoveContext(self, placements, s)

    def evaluate_move(
        self, placements: Mapping[int, Placement], s: int, target: Placement | None
    ) -> MoveResult:
        """Effect of putting session ``s`` at ``target`` (``None`` unassigns it)."""
        return self.move_context(placements, s).evaluate(target)

    def rule_touches(self, rule: SRule, session: Session) -> bool:
        if session.activity in self.rule_activities[rule.id]:
            return True
        if self.rule_instructors[rule.id] & set(session.instructors):
            return True
        return bool(self.rule_atoms[rule.id] & self.session_atoms[session.index])


class MoveContext:
    """Everything about the other sessions that moving session ``s`` depends on, computed
    once so that many candidate places can be compared quickly."""

    def __init__(self, evaluator: Evaluator, placements: Mapping[int, Placement], s: int) -> None:
        self.ev = evaluator
        p = evaluator.p
        self.s = s
        self.session = p.sessions[s]
        self.current = placements.get(s)
        self.others = {k: v for k, v in placements.items() if k != s}
        self.by_slot: dict[int, list[int]] = defaultdict(list)
        instructors = set(self.session.instructors)
        atoms = evaluator.session_atoms[s]
        self.instructor_slots: dict[int, dict[int, list[int]]] = {
            i: defaultdict(list) for i in instructors
        }
        self.atom_slots: dict[int, dict[int, list[int]]] = {a: defaultdict(list) for a in atoms}
        for other, placement in self.others.items():
            other_session = p.sessions[other]
            covered = evaluator.covered(other_session, placement)
            for slot in covered:
                self.by_slot[slot].append(other)
            for i in instructors.intersection(other_session.instructors):
                for slot in covered:
                    self.instructor_slots[i][slot].append(other)
            for a in atoms & evaluator.session_atoms[other]:
                for slot in covered:
                    self.atom_slots[a][slot].append(other)
        self.rules = [r for r in p.rules if evaluator.rule_touches(r, self.session)]
        self.before = self._terms(self.current)

    def _with(
        self, slot_map: dict[int, list[int]], target: Placement | None
    ) -> dict[int, list[int]]:
        result = {slot: list(sessions) for slot, sessions in slot_map.items()}
        if target is not None:
            for slot in self.ev.covered(self.session, target):
                result.setdefault(slot, []).append(self.s)
        return result

    def _terms(self, target: Placement | None) -> tuple[dict[str, int], dict[str, int]]:
        ev, s = self.ev, self.s
        placements = dict(self.others)
        if target is not None:
            placements[s] = target
        values: dict[str, int] = dict.fromkeys(ALL_OBJECTIVES, 0)
        values[UNSCHEDULED] = 0 if target is not None else self.session.duration
        instructor_maps = {i: self._with(m, target) for i, m in self.instructor_slots.items()}
        atom_maps = {a: self._with(m, target) for a, m in self.atom_slots.items()}
        for i, slot_map in instructor_maps.items():
            for code, value in ev.instructor_terms(i, set(slot_map)).items():
                values[code] += value
        for slot_map in atom_maps.values():
            values["student_idle"] += ev.idle_periods(slot_map)
        for code, value in ev.session_terms(s, target).items():
            values[code] += value
        for code, value in ev.activity_terms(self.session.activity, placements).items():
            values[code] += value

        units: dict[str, int] = {}
        for rule in self.rules:
            total = 0
            if rule.type in RESOURCE_RULES:
                for i in ev.rule_instructors[rule.id] & instructor_maps.keys():
                    total += ev.resource_rule_units(
                        rule, set(instructor_maps[i]), instructor_maps[i], placements
                    )
                for a in ev.rule_atoms[rule.id] & atom_maps.keys():
                    total += ev.resource_rule_units(
                        rule, set(atom_maps[a]), atom_maps[a], placements
                    )
            if rule.type not in RESOURCE_RULES or (
                rule.type in SLOT_RULES and ev.rule_activities[rule.id]
            ):
                total += ev.activity_rule_units(rule, placements)
            units[rule.id] = total
        return values, units

    def violations(self, target: Placement) -> list[Violation]:
        ev, p = self.ev, self.ev.p
        found = ev.placement_violations(self.s, target)
        pairs: dict[tuple[str, int], list[int]] = defaultdict(list)
        for slot in ev.covered(self.session, target):
            for other in self.by_slot.get(slot, ()):
                for code in ev.pair_conflicts(self.s, target, other, self.others[other]):
                    pairs[(code, other)].append(slot)
        for (code, other), slots in pairs.items():
            found.append(
                ev.conflict_violation(
                    code, min(self.s, other), max(self.s, other), slots, target.room
                )
            )
        activity = p.activities[self.session.activity]
        if activity.different_days:
            day = p.day_of(target.slot)
            siblings = [
                x
                for x in activity.sessions
                if x != self.s and x in self.others and p.day_of(self.others[x].slot) == day
            ]
            if siblings:
                found.append(
                    Violation(
                        "same_day_occurrences",
                        f"{activity.title}: another occurrence is already on that day.",
                        (self.s, *siblings),
                    )
                )
        return found

    def evaluate(self, target: Placement | None) -> MoveResult:
        ev = self.ev
        violations = self.violations(target) if target is not None else []
        values, units = self._terms(target)
        before_values, before_units = self.before
        objective_deltas = {code: values[code] - before_values[code] for code in values}
        rule_deltas: dict[str, int] = {}
        for rule in self.rules:
            delta = units[rule.id] - before_units[rule.id]
            if rule.enforcement == "hard":
                if units[rule.id] > before_units[rule.id]:
                    violations.append(
                        Violation(
                            f"rule:{rule.type}",
                            f"Rule '{rule.name}' would be broken.",
                            (self.s,),
                            rule_id=rule.id,
                        )
                    )
            elif delta:
                rule_deltas[rule.id] = delta
        tier_deltas = empty_tiers()
        tier_deltas[0] = objective_deltas[UNSCHEDULED]
        for code, (tier, weight) in ev.config.objectives.items():
            tier_deltas[tier] += weight * objective_deltas.get(code, 0)
        for rule in ev.p.rules:
            if rule.id in rule_deltas:
                tier_deltas[rule.tier] += rule.weight * rule_deltas[rule.id]
        return MoveResult(_dedupe(violations), objective_deltas, rule_deltas, tier_deltas)


def _dedupe(violations: list[Violation]) -> list[Violation]:
    seen: set[tuple[str, tuple[int, ...], str]] = set()
    result = []
    for violation in violations:
        key = (violation.code, violation.sessions, violation.message)
        if key not in seen:
            seen.add(key)
            result.append(violation)
    return result
