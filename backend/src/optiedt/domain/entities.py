"""Entities of the domain.

Pure: no I/O, no ORM, no framework imports. Enforced by .importlinter, because
this module is imported by the solver, the analysis layer and the persistence
layer alike — a framework import here leaks into all three.

The Session is the centre of the model. It is the unit CP-SAT places; every
other entity either describes a session or constrains it.

See docs/domain-model.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from optiedt.domain.enums import (
    AvailabilityState,
    ConstraintKind,
    DeclarationSource,
    GroupLevel,
    RecommendationStatus,
    RoomType,
    RunState,
    SessionType,
    TeacherRank,
)

type ProgrammeId = str
type PromotionId = str
type GroupId = str
type StudentId = str
type TeacherId = str
type CourseId = str
type SessionId = str
type RoomId = str
type SlotIndex = int
type ConstraintCode = str  # "H1".."H12", "S2".."S10", "X1".."X4", "SX1"
type RunId = str
type CandidateId = str


# ── Structure of the teaching ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Programme:
    id: ProgrammeId
    code: str
    label: str
    degree_cycle: str
    department: str


@dataclass(frozen=True, slots=True)
class Promotion:
    id: PromotionId
    programme: ProgrammeId
    level: str  # L1, L2, L3, M1, M2
    academic_year: str
    student_count: int


@dataclass(frozen=True, slots=True)
class Group:
    """A promotion, a tutorial group, or a laboratory subgroup.

    One entity for all three levels, linked by ``parent_group``. This is what
    makes H12 expressible: placing a CM occupies every student of every subgroup
    below the promotion, so no session of those subgroups may share the slot.

    The admitted chain is exactly:
        promotion → tutorial group → laboratory subgroup
    """

    id: GroupId
    promotion: PromotionId
    parent_group: GroupId | None
    level: GroupLevel
    label: str
    size: int


@dataclass(frozen=True, slots=True)
class Student:
    """Individual student.

    Used ONLY by the examination model. For the weekly timetable a promotion
    follows a fixed programme, so reasoning on groups loses no information;
    for examinations two students of one group may sit different optional
    courses, so conflicts must be computed per individual. See constraint X1.
    """

    id: StudentId
    promotion: PromotionId
    tutorial_group: GroupId
    laboratory_subgroup: GroupId


@dataclass(frozen=True, slots=True)
class Teacher:
    id: TeacherId
    department: str
    rank: TeacherRank
    max_hours_per_week: int  # 9, 12, 18 or 24 by rank


@dataclass(frozen=True, slots=True)
class Course:
    id: CourseId
    code: str
    department: str
    programme: ProgrammeId
    level: str
    semester: int
    credits: int


@dataclass(frozen=True, slots=True)
class Session:
    """The unit to be placed. One slot and one room per session.

    ``duration_periods`` is 1 or 2. **104 of the 218 sessions in the reference
    instance span two periods** — which is why y[s][t] must mean "occupies t",
    not "starts at t". See C-7.

    ``occurrences_per_week`` is 1 for every row of the reference instance, but
    the column exists in ``sessions.csv`` and the schema admits more. If it ever
    exceeds 1, H7 ("each session placed exactly once") no longer holds as
    written and the pre-analysis demand calculation changes with it. Read it;
    do not assume it away.
    """

    id: SessionId
    course: CourseId
    group: GroupId
    teacher: TeacherId
    type: SessionType
    duration_periods: int
    occurrences_per_week: int
    required_room_type: RoomType
    locked: bool  # H10: keeps the slot and room given to it


@dataclass(frozen=True, slots=True)
class Room:
    id: RoomId
    building: str
    code: str
    capacity: int
    type: RoomType
    equipment: tuple[str, ...] = ()


# ── Time and calendar ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Slot:
    """Time unit of the weekly grid, identified by a single integer index.

        index = day_index * periods_per_day + period_index

    ``is_open`` is driven by CalendarConfig and Holiday, never by the model.
    Closing a half-day sets it to False and H9 removes those slots from every
    session's domain. See ADR-003.
    """

    index: SlotIndex
    day_index: int
    period_index: int
    start_hour: time
    end_hour: time
    is_open: bool


@dataclass(frozen=True, slots=True)
class Availability:
    teacher: TeacherId
    slot: SlotIndex
    state: AvailabilityState
    semester: int
    source: DeclarationSource


@dataclass(frozen=True, slots=True)
class Holiday:
    date: date
    label: str
    lunar: bool  # date known only approximately in advance
    approximate: bool
    blocking: bool  # blocking holidays close their slots


@dataclass(frozen=True, slots=True)
class CalendarConfig:
    """Periods per day, closed half-days, shortened-day window.

    Held as data, never written into the model (ADR-003). The shortened-day
    shift moves displayed hours only — the slot index does not change, so no
    variable and no constraint is affected.
    """

    key: str
    value: str


@dataclass(frozen=True, slots=True)
class ConstraintDefinition:
    """One row of constraint_catalogue.csv — 12 hard + 7 soft = 19.

    Codes are permanent identifiers used in the catalogue, in the conflict
    report and in weight_delta parameters. S1, S8 and S9 are RETIRED and must
    never be reused.
    """

    code: ConstraintCode
    name: str
    kind: ConstraintKind
    default_weight: float  # 0.0 for hard constraints
    xhstt_reference: str | None


# ── Runs and results ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WeightProfile:
    """Non-negative weights over the soft criteria.

    Catalogue defaults sum to 0.90; a profile renormalises to 1.0 before any
    score is computed, which is what makes two runs' scores comparable.

    Diversity of the portfolio comes from varying the objective, not the seed:
    two candidates from two profiles differ for a reason that is exactly the
    difference between those profiles.
    """

    name: str
    weights: dict[ConstraintCode, float]


@dataclass(frozen=True, slots=True)
class Run:
    """One execution of the generation.

    The seed, weights, bounds and model version are recorded so a published
    timetable traces back to what produced it — an acceptance criterion.
    """

    id: RunId
    created_at: datetime
    seed: int
    deterministic_budget: float  # NOT wall-clock seconds — see ADR-011
    state: RunState
    model_version: str


@dataclass(frozen=True, slots=True)
class Placement:
    """One assignment inside one candidate. Written only by the solver."""

    session: SessionId
    slot: SlotIndex
    room: RoomId


@dataclass(frozen=True, slots=True)
class SubScore:
    """One criterion's value for one candidate.

    ``normalised`` is in [0, 1] with 1 the best situation, computed against
    instance-derived bounds (ADR-009).
    """

    criterion: ConstraintCode
    raw_value: float
    normalised: float


@dataclass(frozen=True, slots=True)
class Candidate:
    """A valid timetable produced by one run under one weight profile.

    IMMUTABLE once recorded. Its sub-scores describe its content; editing it
    would leave them describing something that no longer exists. A regenerated
    timetable is a NEW candidate under a NEW run.
    """

    id: CandidateId
    run: RunId
    profile_name: str
    cost: int
    score: float  # out of 100
    placements: tuple[Placement, ...]
    sub_scores: tuple[SubScore, ...]


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    """Rules SUFFICIENT to explain an infeasibility — not the smallest such set.

    ⚠️ **Lives in `domain`, not in `solver`, deliberately (Phase 5 M2).** It is
    a RESULT — a tuple of catalogue codes and three facts about them — carried
    from the solver to the run record, to the API and to the screen. Leaving it
    in `solver/interfaces.py` would have forced `api/schemas.py` to reach it
    through a re-export in `services`, which is legal under
    `api ⇸ solver` (that contract forbids DIRECT imports only) and would have
    been evasion rather than compliance. A shape three layers must name belongs
    to the layer all three may import.

    The subset returned by the solver is heuristically reduced and is NOT
    guaranteed minimal. The interface must present it as "rules sufficient to
    explain the conflict". Obtaining a minimal set would require minimising the
    sum of the literals instead, recorded as a possible improvement.

    ⚠️ **An empty `conflicting_codes` is not one outcome but two**, and
    collapsing them would be the same mistake as an empty pre-analysis list
    reading as "verified, nothing wrong":

    - `is_conclusive=True`, empty — the solver proved infeasibility, and **no
      relaxable rule explains it**. Only H1, H3, H7 and H12 carry literals
      (C-6); H4, H5, H6, H8, H9 and H10 are domain restrictions applied when
      the variable is built, so there is nothing to relax. The conflict is in
      the data, and the pre-analysis report is where to look.
    - `is_conclusive=False`, empty — the solver could **not prove**
      infeasibility within the budget. That is the C-13 shape: an instance can
      genuinely have no solution while CP-SAT's propagators cannot construct
      the proof. Never present this as "no conflict found".

    `detail` carries which of those happened, in words, because the codes alone
    cannot say it.
    """

    conflicting_codes: tuple[ConstraintCode, ...]
    is_minimal: bool = False
    is_conclusive: bool = True
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Comparison:
    """A recorded preference. The only training data increment 2 will have."""

    run: RunId
    retained: CandidateId
    set_aside: CandidateId
    user: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Publication:
    candidate: CandidateId
    published_at: datetime
    user: str


@dataclass(frozen=True, slots=True)
class RecommendationRecord:
    """An AI proposal and its outcome.

    ``action`` is one of the three catalogue variants; see
    optiedt.recommendations.catalogue. ``resulting_candidate`` is set only when
    the recommendation was accepted and the regenerated run produced one.
    """

    id: str
    candidate: CandidateId
    criterion: ConstraintCode | None
    status: RecommendationStatus
    resulting_candidate: CandidateId | None
