"""FR-12 — the five verifications, inside the application.

The working logic already existed outside it, in
``data/verification/verify_instance.py``, which guards the contract between the
generator and the application and runs on every ``scripts/run-checks.ps1``.
This module is the in-application port: same arithmetic, same figures, reported
through the API as structural risks instead of printed to a console.

**The two implementations are kept independent on purpose.** The standalone
checker depends on nothing — not on this package, not on the domain entities,
not even on a third-party import — because the 13 CSVs are the contract and a
checker that guards a contract must not depend on either side of it
(docs/data-and-instance.md). So the same arithmetic is written twice, and
``tests/integration/test_preanalysis_matches_verifier.py`` requires the two to
agree figure for figure on the reference instance. That is the same guard
``tests/integration/test_objective_matches_analysis.py`` puts on the other
deliberate duplication in this project, and for the same reason: two
implementations of one definition drift silently unless something compares
them numerically.

⚠️ **SLOT_COVERAGE applies BOTH bounds, and shipping the period bound alone
would have put the C-13 blind spot inside the product.** The period bound is
necessary but not sufficient: it reported a comfortable 95.2 % for an instance
that had no solution at all, and three sessions went looking for a solver bug
that did not exist. Every check below states which kind it is.

May NOT import the solver — enforced by .importlinter. If it could call the
solver it would stop being the instrument that tells a genuinely infeasible
instance apart from a modelling regression.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from optiedt.domain.entities import GroupId, RoomId, Session, SlotIndex, TeacherId
from optiedt.domain.enums import AvailabilityState, GroupLevel, RoomType
from optiedt.domain.instance import Instance
from optiedt.preanalysis.checks import (
    CHECK_GROUP_HIERARCHY,
    CHECK_ROOM_SUITABILITY,
    CHECK_SLOT_COVERAGE,
    CHECK_TEACHER_FREE_SLOTS,
    CHECK_TEACHER_LOAD,
    CheckResult,
)

DEFAULT_PERIOD_MINUTES = 90
"""Fallback when calendar_config carries no period_minutes.

The reference instance carries it (90), and reading it rather than hardcoding
1.5 hours per period is what ADR-003 means by institutional rules being
configuration: a faculty running 60-minute periods changes a CSV, not this file.
"""

SATURATION_PERCENT = 90.0
"""Above this a check still PASSES but says the resource is the binding one.

Not a threshold with any authority behind it — it is the level at which the
reference instance's computer laboratories sit (90.9 % of two-period windows,
8 spare in the week), and at that saturation withdrawing one room makes the
instance infeasible. A report that only said "passed" would hide that.
"""


# ── Shared arithmetic ──────────────────────────────────────────────────


def demand_periods(session: Session) -> int:
    """Periods this session consumes in a week, occurrences included."""
    return session.duration_periods * session.occurrences_per_week


def open_slot_count(instance: Instance) -> int:
    return sum(1 for s in instance.slots if s.is_open)


def contiguous_open_runs(instance: Instance) -> tuple[int, ...]:
    """Lengths of the maximal runs of consecutive open slots, within each day.

    ⚠️ Within each DAY, not across the week — this is where H8 enters the
    arithmetic. A multi-period session must keep its periods consecutive (it is
    one interval) and inside one day, so the week's open slots are not a flat
    pool: on the reference calendar they are six runs, five of length 5 and one
    of length 3 (Saturday afternoon closed).
    """
    by_day: dict[int, list[SlotIndex]] = defaultdict(list)
    for slot in instance.slots:
        if slot.is_open:
            by_day[slot.day_index].append(slot.index)

    runs: list[int] = []
    for day_slots in by_day.values():
        length = 0
        previous: SlotIndex | None = None
        for index in sorted(day_slots):
            if previous is not None and index == previous + 1:
                length += 1
            else:
                if length:
                    runs.append(length)
                length = 1
            previous = index
        if length:
            runs.append(length)
    return tuple(runs)


def windows_per_room(runs: tuple[int, ...], duration: int) -> int:
    """Disjoint `duration`-period windows one room offers across the week.

    A run of length L offers floor(L / duration) of them, whatever the period
    count says: with 5-period days and 2-period sessions one period per
    room-day is structurally unusable, so a room offers 11 two-period windows a
    week rather than 28 periods' worth — a fifth of the apparent capacity does
    not exist. Each such session occupies a disjoint window inside some run, so
    the bound holds no matter what else shares the run.
    """
    return sum(length // duration for length in runs)


def period_hours(instance: Instance) -> float:
    raw = instance.calendar_config.get("period_minutes")
    minutes = int(raw) if raw is not None and raw.strip() else DEFAULT_PERIOD_MINUTES
    return minutes / 60.0


def rooms_by_type(instance: Instance) -> dict[RoomType, list[RoomId]]:
    grouped: dict[RoomType, list[RoomId]] = defaultdict(list)
    for room in instance.rooms:
        grouped[room.type].append(room.id)
    return grouped


def group_sizes(instance: Instance) -> dict[GroupId, int]:
    return {g.id: g.size for g in instance.groups}


def teacher_load_periods(instance: Instance) -> Counter[TeacherId]:
    load: Counter[TeacherId] = Counter()
    for session in instance.sessions:
        load[session.teacher] += demand_periods(session)
    return load


def declared_unavailable(instance: Instance) -> Counter[TeacherId]:
    counted: Counter[TeacherId] = Counter()
    for row in instance.availability:
        if row.state is AvailabilityState.UNAVAILABLE:
            counted[row.teacher] += 1
    return counted


# ── 1. Room suitability ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RoomSuitability:
    """Each session finds a room of the required type and sufficient capacity.

    SUFFICIENT for what it claims: if it fails, no assignment exists, because
    the session has nowhere at all to go. It says nothing about whether the
    suitable rooms are free at the same time — that is SLOT_COVERAGE's job.

    This is the arithmetic form of H4 and H5, which the solver applies by
    pruning `candidate_rooms` (solver/variables.py). `build_variables` raises
    when the pruning leaves a session with no room; running this check first is
    how that becomes a named report rather than an exception.
    """

    @property
    def name(self) -> str:
        return CHECK_ROOM_SUITABILITY

    def run(self, instance: Instance) -> CheckResult:
        sizes = group_sizes(instance)
        by_type = rooms_by_type(instance)
        largest: dict[RoomType, int] = {}
        for room in instance.rooms:
            largest[room.type] = max(largest.get(room.type, 0), room.capacity)

        unplaceable: list[tuple[Session, int]] = []
        for session in instance.sessions:
            size = sizes.get(session.group, 0)
            available = largest.get(session.required_room_type, 0)
            if available < size:
                unplaceable.append((session, size - available))

        if not unplaceable:
            return CheckResult(
                name=self.name,
                passed=True,
                detail=(
                    f"0 of {len(instance.sessions)} sessions without a suitable room; "
                    f"room types present: "
                    + ", ".join(f"{t} x{len(r)}" for t, r in sorted(by_type.items()))
                ),
            )

        worst_session, worst_gap = max(unplaceable, key=lambda pair: pair[1])
        return CheckResult(
            name=self.name,
            passed=False,
            resource=str(worst_session.required_room_type),
            missing_quantity=float(worst_gap),
            detail=(
                f"{len(unplaceable)} session(s) have no room of the required type with "
                f"enough capacity. Worst: {worst_session.id} needs a "
                f"{worst_session.required_room_type} seating "
                f"{sizes.get(worst_session.group, 0)}, the largest is "
                f"{largest.get(worst_session.required_room_type, 0)} — short by {worst_gap} "
                f"places. No timetable exists; add capacity or split the group."
            ),
        )


# ── 2. Slot coverage — the check that must carry both bounds ───────────


@dataclass(frozen=True, slots=True)
class TypeCoverage:
    """One room type's two bounds, kept together so neither is read alone."""

    room_type: RoomType
    rooms: int
    periods_required: int
    periods_available: int
    window_demand: dict[int, int]
    """Sessions needing a window of that duration, by duration (>= 2 only)."""

    window_supply: dict[int, int]
    """Disjoint windows of that duration the type's rooms offer in a week."""

    @property
    def period_percent(self) -> float:
        if self.periods_available == 0:
            return float("inf")
        return 100.0 * self.periods_required / self.periods_available

    def window_percent(self, duration: int) -> float:
        supply = self.window_supply.get(duration, 0)
        if supply == 0:
            return float("inf")
        return 100.0 * self.window_demand.get(duration, 0) / supply

    def shortfalls(self) -> list[tuple[str, int]]:
        """Every way this type is over-subscribed, with the quantity missing."""
        found: list[tuple[str, int]] = []
        if self.periods_required > self.periods_available:
            found.append(("periods", self.periods_required - self.periods_available))
        for duration, count in sorted(self.window_demand.items()):
            supply = self.window_supply.get(duration, 0)
            if count > supply:
                found.append((f"{duration}-period windows", count - supply))
        return found


def coverage_by_type(instance: Instance) -> list[TypeCoverage]:
    runs = contiguous_open_runs(instance)
    open_slots = open_slot_count(instance)
    by_type = rooms_by_type(instance)

    periods_required: Counter[RoomType] = Counter()
    window_demand: dict[RoomType, Counter[int]] = defaultdict(Counter)
    for session in instance.sessions:
        periods_required[session.required_room_type] += demand_periods(session)
        if session.duration_periods >= 2:
            window_demand[session.required_room_type][session.duration_periods] += (
                session.occurrences_per_week
            )

    coverage: list[TypeCoverage] = []
    for room_type in sorted(by_type):
        rooms = len(by_type[room_type])
        demands = dict(window_demand.get(room_type, Counter()))
        coverage.append(
            TypeCoverage(
                room_type=room_type,
                rooms=rooms,
                periods_required=periods_required.get(room_type, 0),
                periods_available=rooms * open_slots,
                window_demand=demands,
                window_supply={d: rooms * windows_per_room(runs, d) for d in demands},
            )
        )
    return coverage


@dataclass(frozen=True, slots=True)
class SlotCoverage:
    """Open slots cover the demand for each room type — under BOTH bounds.

    ⚠️ **The period bound is NECESSARY BUT NOT SUFFICIENT, and reading it alone
    is what let C-13 through.** `periods_required <= rooms * open_slots`
    reasons about area, exactly as CP-SAT's AddCumulative does, and area fits
    for instances that cannot be tiled: a 5-period day does not decompose into
    2-period sessions, so one period per room-day is unusable.

    The contiguity bound is the one that binds here:

        sessions of duration d  <=  rooms * SUM floor(L / d)

    over the week's contiguous open runs. On the original room mix it fires —
    computer laboratories short by 14 windows, science laboratories by 2 —
    while the period bound reported a comfortable 95.2 %. A FAILURE HERE IS A
    PIGEONHOLE PROOF THAT NO TIMETABLE EXISTS, not a warning: it needs no
    solver, and no budget, tuning or reformulation can find a solution that
    does not exist.

    Passing is not the same as being safe, so a type above 90 % is named as the
    binding resource even when the check passes.
    """

    @property
    def name(self) -> str:
        return CHECK_SLOT_COVERAGE

    def run(self, instance: Instance) -> CheckResult:
        coverage = coverage_by_type(instance)
        summary = "; ".join(_describe(c) for c in coverage)

        failing = [(c, s) for c in coverage for s in c.shortfalls()]
        if failing:
            worst_coverage, (_worst_kind, missing) = max(failing, key=lambda pair: pair[1][1])
            detail = (
                f"{len(failing)} bound(s) violated. "
                + " ".join(
                    f"{c.room_type} is short by {missing_n} {kind_n} ({c.rooms} rooms)."
                    for c, (kind_n, missing_n) in failing
                )
                + " This is a pigeonhole argument, not a solver-performance question: "
                "no timetable exists. " + summary
            )
            return CheckResult(
                name=self.name,
                passed=False,
                resource=str(worst_coverage.room_type),
                missing_quantity=float(missing),
                detail=detail,
            )

        binding = [
            c
            for c in coverage
            if c.period_percent > SATURATION_PERCENT
            or any(c.window_percent(d) > SATURATION_PERCENT for d in c.window_demand)
        ]
        note = ""
        if binding:
            names = ", ".join(str(c.room_type) for c in binding)
            note = (
                f" {names} is the binding resource: withdrawing one room makes the "
                "instance very probably infeasible, and at this saturation a modelling "
                "regression surfaces as INFEASIBLE rather than as a slow solve."
            )
        return CheckResult(name=self.name, passed=True, detail=summary + note)


def _describe(coverage: TypeCoverage) -> str:
    parts = [
        f"{coverage.room_type} {coverage.periods_required}/{coverage.periods_available} "
        f"periods = {coverage.period_percent:.1f}%"
    ]
    for duration in sorted(coverage.window_demand):
        supply = coverage.window_supply.get(duration, 0)
        parts.append(
            f"{coverage.window_demand[duration]}/{supply} {duration}-period windows = "
            f"{coverage.window_percent(duration):.1f}%"
        )
    return ", ".join(parts)


# ── 3. Teacher load ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TeacherLoad:
    """No teacher is assigned more hours than the maximum load of their rank.

    NECESSARY, not sufficient: it counts hours and says nothing about whether
    they can be arranged. Hours come from `period_minutes` in the calendar
    configuration, not from a constant here (ADR-003).
    """

    @property
    def name(self) -> str:
        return CHECK_TEACHER_LOAD

    def run(self, instance: Instance) -> CheckResult:
        hours_per_period = period_hours(instance)
        load = teacher_load_periods(instance)
        limits = {t.id: t.max_hours_per_week for t in instance.teachers}

        over: list[tuple[TeacherId, float]] = []
        for teacher_id, limit in limits.items():
            assigned = load.get(teacher_id, 0) * hours_per_period
            if assigned > limit:
                over.append((teacher_id, assigned - limit))

        heaviest = max(load.values(), default=0)
        figures = (
            f"heaviest load {heaviest} periods "
            f"({heaviest * hours_per_period:g} h) over {len(limits)} teachers"
        )
        if not over:
            return CheckResult(
                name=self.name,
                passed=True,
                detail=f"0 teachers above their rank limit; {figures}",
            )

        worst_teacher, worst_excess = max(over, key=lambda pair: pair[1])
        return CheckResult(
            name=self.name,
            passed=False,
            resource=worst_teacher,
            missing_quantity=float(worst_excess),
            detail=(
                f"{len(over)} teacher(s) above the maximum load of their rank. Worst: "
                f"{worst_teacher} carries {load.get(worst_teacher, 0) * hours_per_period:g} h "
                f"against a limit of {limits[worst_teacher]} h — {worst_excess:g} h too many. "
                f"{figures}"
            ),
        )


# ── 4. Teacher free slots ──────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TeacherFreeSlots:
    """Each teacher keeps enough free slots for the sessions assigned.

    NECESSARY, not sufficient: it compares counts per teacher and ignores
    everything about *which* slots those are, so a teacher with a comfortable
    margin can still be unplaceable once H1, H12 and room contention are
    imposed. Its value is the opposite direction — a negative margin means no
    timetable exists, for a reason that names one person.

    This is the arithmetic form of H6 meeting the demand, and it is the check
    that will fire first when the availability grid starts collecting real
    declarations: a teacher who marks most of the week unavailable is caught
    here rather than by a solve that returns INFEASIBLE with nothing to point
    at.
    """

    @property
    def name(self) -> str:
        return CHECK_TEACHER_FREE_SLOTS

    def run(self, instance: Instance) -> CheckResult:
        open_slots = open_slot_count(instance)
        load = teacher_load_periods(instance)
        unavailable = declared_unavailable(instance)

        margins = {
            t.id: (open_slots - unavailable.get(t.id, 0)) - load.get(t.id, 0)
            for t in instance.teachers
        }
        in_difficulty = {t: m for t, m in margins.items() if m < 0}
        smallest = min(margins.values(), default=open_slots)

        if not in_difficulty:
            return CheckResult(
                name=self.name,
                passed=True,
                detail=(
                    f"0 teachers in difficulty; smallest margin {smallest} free slots "
                    f"of {open_slots} open"
                ),
            )

        worst_teacher, worst_margin = min(in_difficulty.items(), key=lambda pair: pair[1])
        return CheckResult(
            name=self.name,
            passed=False,
            resource=worst_teacher,
            missing_quantity=float(-worst_margin),
            detail=(
                f"{len(in_difficulty)} teacher(s) have fewer free slots than sessions to "
                f"place. Worst: {worst_teacher} needs {load.get(worst_teacher, 0)} periods "
                f"but keeps only {open_slots - unavailable.get(worst_teacher, 0)} slots free "
                f"— short by {-worst_margin}. Withdraw a declared unavailability or move a "
                f"session to another teacher."
            ),
        )


# ── 5. Group hierarchy ─────────────────────────────────────────────────

_ADMITTED_PARENT: dict[GroupLevel, GroupLevel | None] = {
    GroupLevel.PROMO: None,
    GroupLevel.TD: GroupLevel.PROMO,
    GroupLevel.TP: GroupLevel.TD,
}
"""Exactly one chain is admitted: promotion -> tutorial group -> subgroup.

H12 walks a group's ancestor chain and `solver/constraints/overlap.py` relies
on that chain being a genuine forest. A cycle would make it loop; a TP hanging
off a promotion would make a CM fail to gather the subgroup it should.
"""


@dataclass(frozen=True, slots=True)
class GroupHierarchy:
    """The promotion -> tutorial group -> laboratory subgroup chain is consistent.

    NECESSARY: a broken chain does not by itself prove infeasibility, it proves
    the instance is malformed — H12 would then forbid the wrong pairs, and the
    timetable produced would be wrong rather than absent, which is worse.

    ⚠️ **One half of the standalone verifier's check cannot be performed here,
    and saying so is the point.** `verify_instance.py` also confirms that the
    425 students match the declared subgroup sizes. `Instance` deliberately
    excludes `Student` (domain/instance.py): the students exist only for the
    examination model, increment 2, and loading them would be dead weight in
    every solve. That half stays with `scripts/verify-instance.ps1`, and the
    detail below says so rather than letting a narrower check pass for the
    documented one.
    """

    @property
    def name(self) -> str:
        return CHECK_GROUP_HIERARCHY

    def run(self, instance: Instance) -> CheckResult:
        by_id = {g.id: g for g in instance.groups}

        dangling = [g.id for g in instance.groups if g.parent_group and g.parent_group not in by_id]

        wrong_level: list[GroupId] = []
        for group in instance.groups:
            expected = _ADMITTED_PARENT[group.level]
            parent = by_id.get(group.parent_group) if group.parent_group else None
            if (expected is None and group.parent_group is not None) or (
                expected is not None
                and (parent is None or parent.level is not expected)
                # A dangling reference is already reported above; naming it
                # twice would inflate the count the report shows.
                and group.id not in dangling
            ):
                wrong_level.append(group.id)

        cyclic: list[GroupId] = []
        for group in instance.groups:
            seen: set[GroupId] = set()
            current: GroupId | None = group.id
            while current is not None and current in by_id:
                if current in seen:
                    cyclic.append(group.id)
                    break
                seen.add(current)
                current = by_id[current].parent_group

        levels = Counter(g.level for g in instance.groups)
        figures = " / ".join(f"{lvl} {levels.get(lvl, 0)}" for lvl in GroupLevel)
        caveat = (
            " Student counts against declared sizes are NOT checked here — Instance "
            "excludes Student by design (increment 2); scripts/verify-instance.ps1 "
            "covers that half."
        )

        broken = dangling + wrong_level + cyclic
        if not broken:
            return CheckResult(
                name=self.name,
                passed=True,
                detail=(
                    f"0 invalid parent references, 0 invalid chains, 0 cycles; {figures}.{caveat}"
                ),
            )

        return CheckResult(
            name=self.name,
            passed=False,
            resource=broken[0],
            missing_quantity=float(len(broken)),
            detail=(
                f"{len(dangling)} dangling parent reference(s), {len(wrong_level)} group(s) "
                f"outside the admitted promotion -> TD -> TP chain, {len(cyclic)} in a cycle. "
                f"First: {broken[0]}. H12 walks this chain, so a break makes the solver "
                f"forbid the wrong pairs rather than fail.{caveat}"
            ),
        )


# ── The five, in the order they are reported ───────────────────────────

ALL_CHECKS = (
    RoomSuitability(),
    SlotCoverage(),
    TeacherLoad(),
    TeacherFreeSlots(),
    GroupHierarchy(),
)


@dataclass(frozen=True, slots=True)
class DefaultPreAnalysis:
    """Stage 1 of every run (FR-12).

    Runs all five and returns every result, passing or failing — the report is
    the evidence that the instance was checked, so a clean run must be
    distinguishable from a run that skipped the stage. That distinction is
    exactly why `RunOut` omitted `preAnalysis` entirely until this landed: an
    empty list would have read as "verified, nothing wrong" when it meant
    "never verified", which is the confusion that cost three sessions on C-13.

    It does not decide anything. A failing check does not stop the run: the
    pipeline always runs stage 1 then stage 2 (docs/architecture.md), so the
    solver's own verdict is still obtained and the diagnosis run can name the
    rules in conflict. Reporting a structural proof of infeasibility AND the
    conflict set is more useful than either alone.
    """

    def verify(self, instance: Instance) -> list[CheckResult]:
        return [check.run(instance) for check in ALL_CHECKS]
