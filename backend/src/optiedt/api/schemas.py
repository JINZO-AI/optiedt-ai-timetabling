"""Request and response shapes of the REST surface.

These are the wire format, deliberately separate from `optiedt.domain`. The
domain layer is pure and must stay free of framework imports (.importlinter
forbids `domain -> fastapi`), so it cannot carry Pydantic models itself; and a
wire format that IS the domain model cannot be evolved without changing the
domain.

Two rules the frontend depends on:

1. **Field names are camelCase on the wire**, matching
   `frontend/src/types/domain.ts`. The alias generator does this once here
   rather than each model spelling it out.

2. **Enum values are the French literals**, unchanged: `Amphi`, `Salle`,
   `Lab_Info`, `Lab_Sciences`, `CM`, `TD`, `TP`, `PROMO`. They are the literals
   in the instance CSVs (CLAUDE.md, "Conventions"), and translating them at the
   API boundary would create the mapping layer the project exists without.
   `StrEnum` gives this for free, and `tests/unit/test_api_schemas.py` pins it
   so a later "tidy-up" cannot quietly anglicise the wire format.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from optiedt.analysis.interfaces import (
    Contribution,
    Decomposition,
    DominanceVerdict,
    Recommendation,
)
from optiedt.domain.entities import (
    Availability,
    Candidate,
    ConstraintDefinition,
    Course,
    DiagnosisResult,
    Group,
    Placement,
    Programme,
    Promotion,
    Room,
    Session,
    Slot,
    SubScore,
    Teacher,
    User,
)
from optiedt.domain.enums import (
    AvailabilityState,
    ConstraintKind,
    DeclarationSource,
    GroupLevel,
    RoomType,
    RunState,
    SessionType,
    TeacherRank,
    UserRole,
)
from optiedt.domain.instance import Instance
from optiedt.preanalysis.checks import CheckResult
from optiedt.services.runs import RunRecord


class ApiModel(BaseModel):
    """Base for every wire model: camelCase aliases, immutable."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


# ── Authentication (FR-11) ─────────────────────────────────────────────


class TokenOut(ApiModel):
    """⚠️ `access_token` and `token_type` are snake_case ON THE WIRE.

    Every other model here is camelCase, and this one deliberately is not: the
    OAuth2 password flow fixes these field names, and FastAPI's own `/api/docs`
    "Authorize" button reads them. Renaming them to match house style would
    break the generated documentation's sign-in for a consistency nobody
    benefits from. `frontend/src/api/client.ts` reads them as spelled here.

    ⚠️ `alias_generator=None` is REQUIRED and is not tidiness. Pydantic MERGES
    `model_config` with the base class's rather than replacing it, so declaring
    only `frozen=True` here left `ApiModel`'s camelCase generator in force and
    the endpoint answered `accessToken`/`tokenType` — a 200 whose body no
    OAuth2 client can read. Caught by `test_rbac.py` on its first run.
    """

    model_config = ConfigDict(alias_generator=None, frozen=True)

    access_token: str
    token_type: str


class UserOut(ApiModel):
    """The signed-in account. ⚠️ Carries NO credential, by construction —
    `domain.User` has no password field for this to expose."""

    id: str
    username: str
    role: UserRole
    teacher: str | None

    @classmethod
    def of(cls, u: User) -> UserOut:
        return cls(id=u.id, username=u.username, role=u.role, teacher=u.teacher)


# ── Structure of the teaching ──────────────────────────────────────────


class ProgrammeOut(ApiModel):
    id: str
    code: str
    label: str
    degree_cycle: str
    department: str

    @classmethod
    def of(cls, p: Programme) -> ProgrammeOut:
        return cls(
            id=p.id,
            code=p.code,
            label=p.label,
            degree_cycle=p.degree_cycle,
            department=p.department,
        )


class PromotionOut(ApiModel):
    id: str
    programme: str
    level: str
    academic_year: str
    student_count: int

    @classmethod
    def of(cls, p: Promotion) -> PromotionOut:
        return cls(
            id=p.id,
            programme=p.programme,
            level=p.level,
            academic_year=p.academic_year,
            student_count=p.student_count,
        )


class GroupOut(ApiModel):
    id: str
    promotion: str
    parent_group: str | None
    level: GroupLevel
    label: str
    size: int

    @classmethod
    def of(cls, g: Group) -> GroupOut:
        return cls(
            id=g.id,
            promotion=g.promotion,
            parent_group=g.parent_group,
            level=g.level,
            label=g.label,
            size=g.size,
        )


class TeacherOut(ApiModel):
    id: str
    department: str
    rank: TeacherRank
    max_hours_per_week: int

    @classmethod
    def of(cls, t: Teacher) -> TeacherOut:
        return cls(
            id=t.id,
            department=t.department,
            rank=t.rank,
            max_hours_per_week=t.max_hours_per_week,
        )


class CourseOut(ApiModel):
    id: str
    code: str
    department: str
    programme: str
    level: str
    semester: int
    credits: int

    @classmethod
    def of(cls, c: Course) -> CourseOut:
        return cls(
            id=c.id,
            code=c.code,
            department=c.department,
            programme=c.programme,
            level=c.level,
            semester=c.semester,
            credits=c.credits,
        )


class SessionOut(ApiModel):
    id: str
    course: str
    group: str
    teacher: str
    type: SessionType
    duration_periods: int
    occurrences_per_week: int
    required_room_type: RoomType
    locked: bool

    @classmethod
    def of(cls, s: Session) -> SessionOut:
        return cls(
            id=s.id,
            course=s.course,
            group=s.group,
            teacher=s.teacher,
            type=s.type,
            duration_periods=s.duration_periods,
            occurrences_per_week=s.occurrences_per_week,
            required_room_type=s.required_room_type,
            locked=s.locked,
        )


class RoomOut(ApiModel):
    id: str
    building: str
    code: str
    capacity: int
    type: RoomType
    equipment: list[str]

    @classmethod
    def of(cls, r: Room) -> RoomOut:
        return cls(
            id=r.id,
            building=r.building,
            code=r.code,
            capacity=r.capacity,
            type=r.type,
            equipment=list(r.equipment),
        )


# ── Time and calendar ──────────────────────────────────────────────────


class SlotOut(ApiModel):
    """One cell of the weekly grid.

    Hours are rendered "HH:MM" rather than as ISO times: they are displayed,
    never computed with. `is_open` is driven by the calendar configuration and
    H9 (ADR-003) — the interface reads it and must never special-case a closed
    day of its own accord, which is invariant 7.
    """

    index: int
    day_index: int
    period_index: int
    start_hour: str
    end_hour: str
    is_open: bool

    @classmethod
    def of(cls, s: Slot) -> SlotOut:
        return cls(
            index=s.index,
            day_index=s.day_index,
            period_index=s.period_index,
            start_hour=s.start_hour.strftime("%H:%M"),
            end_hour=s.end_hour.strftime("%H:%M"),
            is_open=s.is_open,
        )


class AvailabilityOut(ApiModel):
    """A declaration. `source` distinguishes a generated row from a real one.

    That distinction is a requirement, not a convenience (docs/domain-model.md):
    generated declarations exist only so the instance is solvable before any
    teacher has connected, and the grid must be able to show which is which.
    """

    teacher: str
    slot: int
    state: AvailabilityState
    semester: int
    source: DeclarationSource

    @classmethod
    def of(cls, a: Availability) -> AvailabilityOut:
        return cls(
            teacher=a.teacher,
            slot=a.slot,
            state=a.state,
            semester=a.semester,
            source=a.source,
        )


class ConstraintOut(ApiModel):
    code: str
    name: str
    kind: ConstraintKind
    default_weight: float
    xhstt_reference: str | None

    @classmethod
    def of(cls, c: ConstraintDefinition) -> ConstraintOut:
        return cls(
            code=c.code,
            name=c.name,
            kind=c.kind,
            default_weight=c.default_weight,
            xhstt_reference=c.xhstt_reference,
        )


# ── The instance as one payload ────────────────────────────────────────


class InstanceOut(ApiModel):
    """Everything a screen needs to render placements and the grid.

    Sent whole rather than paged: the reference instance is 218 sessions, 51
    groups, 44 teachers, 20 rooms and 30 slots, so the payload is small and one
    request removes a class of loading states from every screen.
    """

    programmes: list[ProgrammeOut]
    promotions: list[PromotionOut]
    groups: list[GroupOut]
    teachers: list[TeacherOut]
    courses: list[CourseOut]
    sessions: list[SessionOut]
    rooms: list[RoomOut]
    slots: list[SlotOut]
    constraints: list[ConstraintOut]
    calendar_config: dict[str, str]

    @classmethod
    def of(cls, instance: Instance) -> InstanceOut:
        return cls(
            programmes=[ProgrammeOut.of(p) for p in instance.programmes],
            promotions=[PromotionOut.of(p) for p in instance.promotions],
            groups=[GroupOut.of(g) for g in instance.groups],
            teachers=[TeacherOut.of(t) for t in instance.teachers],
            courses=[CourseOut.of(c) for c in instance.courses],
            sessions=[SessionOut.of(s) for s in instance.sessions],
            rooms=[RoomOut.of(r) for r in instance.rooms],
            slots=[SlotOut.of(s) for s in instance.slots],
            constraints=[ConstraintOut.of(c) for c in instance.constraints],
            calendar_config=dict(instance.calendar_config),
        )


# ── Availability declaration ───────────────────────────────────────────


class AvailabilityCellIn(ApiModel):
    """One cell the teacher marked. Only non-AVAILABLE cells need be sent.

    ⚠️ `state` admits PREFERRED because the enum does, but the instance schema
    carries no representation for it (C-12): `teacher_availability.csv` has a
    boolean. Whether the grid offers two states or three is an open decision
    for Phase 4 — see C-12 in docs/open-questions.md. The wire format is left
    able to express three so that resolving it does not become an API change.
    """

    slot: int
    state: AvailabilityState


class AvailabilityIn(ApiModel):
    semester: int
    cells: list[AvailabilityCellIn]


# ── Runs and results ───────────────────────────────────────────────────


class RunCreateIn(ApiModel):
    """What a client may choose about a run. Deliberately little.

    The weight profiles are not client-supplied: they are the three of
    `docs/constraint-model.md`. Letting a client post arbitrary profiles would
    make two runs incomparable with nothing recording why.
    """

    seed: int | None = None
    deterministic_budget: float | None = None


class RunCreatedOut(ApiModel):
    """The 202 body. Solving takes minutes; the client polls `GET /runs/{id}`."""

    run_id: str


class PlacementOut(ApiModel):
    session: str
    slot: int
    room: str

    @classmethod
    def of(cls, p: Placement) -> PlacementOut:
        return cls(session=p.session, slot=p.slot, room=p.room)


class SubScoreOut(ApiModel):
    criterion: str
    raw_value: float
    normalised: float

    @classmethod
    def of(cls, s: SubScore) -> SubScoreOut:
        return cls(criterion=s.criterion, raw_value=s.raw_value, normalised=s.normalised)


class CandidateOut(ApiModel):
    """A valid timetable, immutable once recorded (invariant 6).

    ⚠️ `cost` is the solver's objective value, carried as provenance ONLY.
    Nothing ranks, scores or displays a comparison from it: `score` and
    `sub_scores` are recomputed by the analysis layer from the placements,
    which the ban on `analysis -> solver` forces. That indirection stopped
    being theoretical on 2026-07-31, when `CpSolver.objective_value` was
    measured 5-15 units above the objective at the solution actually returned
    under `interleave_search` (ADR-011). **Do not start ranking on `cost`.**
    """

    id: str
    run: str
    profile_name: str
    cost: int
    score: float
    placements: list[PlacementOut]
    sub_scores: list[SubScoreOut]

    @classmethod
    def of(cls, c: Candidate) -> CandidateOut:
        return cls(
            id=c.id,
            run=c.run,
            profile_name=c.profile_name,
            cost=c.cost,
            score=c.score,
            placements=[PlacementOut.of(p) for p in c.placements],
            sub_scores=[SubScoreOut.of(s) for s in c.sub_scores],
        )


class CheckResultOut(ApiModel):
    """One of the five pre-analysis verifications (FR-12).

    ⚠️ A failing check carries the RESOURCE concerned and the QUANTITY missing,
    never a bare boolean — that named detail is the content the structural-risk
    report requires (docs/data-and-instance.md).

    `detail` carries the figures even when the check passes, because passing is
    not the same as being safe: computer laboratories sit at 90.9 % of their
    two-period windows, 8 spare in the whole week, and a report that only said
    "passed" would hide the number most worth watching.
    """

    name: str
    passed: bool
    resource: str | None
    missing_quantity: float | None
    detail: str

    @classmethod
    def of(cls, c: CheckResult) -> CheckResultOut:
        return cls(
            name=c.name,
            passed=c.passed,
            resource=c.resource,
            missing_quantity=c.missing_quantity,
            detail=c.detail,
        )


class DiagnosisOut(ApiModel):
    """FR-8 — rules SUFFICIENT to explain an infeasibility (Phase 5 M2).

    ⚠️ **Never present this as the smallest conflict set.** `isMinimal` is
    False and the subset CP-SAT returns is heuristically reduced.

    ⚠️ **An empty `conflictingCodes` is two different outcomes**, and only
    `isConclusive` tells them apart: conclusive-and-empty means no *relaxable*
    rule explains the conflict (H4-H6, H8-H10 are domain restrictions and
    cannot be relaxed, so the conflict is in the data); inconclusive means
    CP-SAT could not prove the infeasibility at all — which is NOT evidence
    that the instance is sound. `detail` says which in words.
    """

    conflicting_codes: list[str]
    is_minimal: bool
    is_conclusive: bool
    detail: str

    @classmethod
    def of(cls, d: DiagnosisResult) -> DiagnosisOut:
        return cls(
            conflicting_codes=list(d.conflicting_codes),
            is_minimal=d.is_minimal,
            is_conclusive=d.is_conclusive,
            detail=d.detail,
        )


class RunOut(ApiModel):
    """One run and its candidates.

    `preAnalysis` landed with Phase 5 M1 and is present from `PREANALYSIS`
    onwards. ⚠️ **An empty list means the stage did not run** — a `PENDING` run,
    or a failure before stage 1 — and never "verified, nothing wrong". That
    distinction is why the field was omitted entirely rather than sent empty
    while the checks had no implementation; it is precisely the confusion that
    cost three sessions on C-13.

    `diagnosis` landed with M2 and is `null` on every run that reached a
    timetable — stage 3 is entered only from `INFEASIBLE`. ⚠️ A non-null
    diagnosis does **not** mean a conflict was named; read `isConclusive` and
    `conflictingCodes`.
    """

    id: str
    created_at: datetime
    seed: int
    deterministic_budget: float
    """Deterministic time, NOT wall-clock seconds (ADR-011). The interface must
    not present it as a duration."""

    state: RunState
    model_version: str
    weights: dict[str, float]
    """The weights in force — one vector prices every candidate of this run."""

    pre_analysis: list[CheckResultOut]
    """The five checks, in the order they are reported. Empty means not run."""

    diagnosis: DiagnosisOut | None
    """Stage 3's report. `null` unless the run reached `DIAGNOSED`."""

    candidates: list[CandidateOut]
    duplicates_removed: list[str]
    """Profile names whose timetable was identical to one already obtained.

    Reported rather than silently dropped: C-5 turns on how often duplicates
    actually occur, and a mechanism that removes them without saying so would
    hide the evidence needed to settle it.
    """

    deterministic_time_used: float
    wall_clock_seconds: float
    error: str | None

    @classmethod
    def of(cls, record: RunRecord) -> RunOut:
        return cls(
            id=record.run.id,
            created_at=record.run.created_at,
            seed=record.run.seed,
            deterministic_budget=record.run.deterministic_budget,
            state=record.run.state,
            model_version=record.run.model_version,
            weights=dict(record.weights),
            pre_analysis=[CheckResultOut.of(c) for c in record.pre_analysis],
            diagnosis=(DiagnosisOut.of(record.diagnosis) if record.diagnosis is not None else None),
            candidates=[CandidateOut.of(c) for c in record.candidates],
            duplicates_removed=list(record.duplicates_removed),
            deterministic_time_used=record.deterministic_time_used,
            wall_clock_seconds=record.wall_clock_seconds,
            error=record.error,
        )


class RunSummaryOut(ApiModel):
    """A run without its placements, for a list screen."""

    id: str
    created_at: datetime
    seed: int
    state: RunState
    candidate_count: int
    duplicates_removed: list[str]

    @classmethod
    def of(cls, record: RunRecord) -> RunSummaryOut:
        return cls(
            id=record.run.id,
            created_at=record.run.created_at,
            seed=record.run.seed,
            state=record.run.state,
            candidate_count=len(record.candidates),
            duplicates_removed=list(record.duplicates_removed),
        )


# ── Comparison ─────────────────────────────────────────────────────────


class ContributionOut(ApiModel):
    """One criterion's part of the difference between two scores.

        contribution_i = 100 * w_i * ( n_i(A) - n_i(B) )

    These are the figures the comparison screen displays. It must show them,
    not summarise them: their sum IS the score difference, and that identity is
    the explanation feature.
    """

    criterion: str
    weight: float
    normalised_a: float
    normalised_b: float
    value: float

    @classmethod
    def of(cls, c: Contribution) -> ContributionOut:
        return cls(
            criterion=c.criterion,
            weight=c.weight,
            normalised_a=c.normalised_a,
            normalised_b=c.normalised_b,
            value=c.value,
        )


class DecompositionOut(ApiModel):
    candidate_a: str
    candidate_b: str
    score_difference: float
    contributions: list[ContributionOut]

    @classmethod
    def of(cls, d: Decomposition) -> DecompositionOut:
        return cls(
            candidate_a=d.candidate_a,
            candidate_b=d.candidate_b,
            score_difference=d.score_difference,
            contributions=[ContributionOut.of(c) for c in d.contributions],
        )


class DominanceVerdictOut(ApiModel):
    """A candidate another improves on across the board.

    ⚠️ `dominated_by` is never set for the TOP-ranked candidate — that state is
    provably unreachable under a linear weighted sum with non-negative weights
    (C-14). A dominated runner-up is ordinary. Do not build a "top candidate is
    dominated" indicator from this field.
    """

    candidate: str
    dominated_by: str | None

    @classmethod
    def of(cls, d: DominanceVerdict) -> DominanceVerdictOut:
        return cls(candidate=d.candidate, dominated_by=d.dominated_by)


class RecommendedCandidateOut(ApiModel):
    """FR-16 — which candidate the system puts forward, and the rule.

    ⚠️ Named `RecommendedCandidate`, not `Recommendation`, on purpose. The
    domain's `RecommendationRecord` (and `Recommendation` in
    `frontend/src/types/domain.ts`) is a different thing entirely: one of the
    closed 3-action catalogue, `weight_delta` / `lock_session` /
    `exclude_slot`, which belongs to regeneration (FR-23, Phase 5). Two
    unrelated concepts sharing one word is how a screen ends up wired to the
    wrong payload.

    `rule` is carried as text rather than left for the interface to invent,
    because the point of the rule is that it can be CHECKED against the
    sub-scores recorded with the run.
    """

    candidate: str
    rule: str
    score: float
    dominated_by: str | None

    @classmethod
    def of(cls, r: Recommendation) -> RecommendedCandidateOut:
        return cls(candidate=r.candidate, rule=r.rule, score=r.score, dominated_by=r.dominated_by)
