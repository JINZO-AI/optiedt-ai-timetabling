"""Request and response bodies for scenarios, runs and timetable solutions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, ClassVar, Literal

from pydantic import Field, model_validator

from optiedt.api.schemas.common import LongText, Name, Out, Patch, Schema

Mode = Literal["fastest", "reproducible"]
Seconds = Annotated[int, Field(ge=5, le=86_400)]


# ── scenarios ──────────────────────────────────────────────────────────


class ScenarioIn(Schema):
    name: Name
    description: LongText | None = None
    profile_codes: Annotated[list[str], Field(min_length=1, max_length=8)]
    scope_department_ids: list[uuid.UUID] = []
    base_solution_id: uuid.UUID | None = None
    minimize_changes: bool = False
    solver_mode: Mode = "fastest"
    time_limit_seconds: Seconds = 120
    seed: Annotated[int, Field(ge=0, le=2_147_483_647)] = 1


class ScenarioPatch(Patch):
    required_fields: ClassVar[frozenset[str]] = frozenset(
        {
            "name",
            "profile_codes",
            "scope_department_ids",
            "minimize_changes",
            "solver_mode",
            "time_limit_seconds",
            "seed",
        }
    )
    name: Name | None = None
    description: LongText | None = None
    profile_codes: Annotated[list[str], Field(min_length=1, max_length=8)] | None = None
    scope_department_ids: list[uuid.UUID] | None = None
    base_solution_id: uuid.UUID | None = None
    minimize_changes: bool | None = None
    solver_mode: Mode | None = None
    time_limit_seconds: Seconds | None = None
    seed: Annotated[int, Field(ge=0, le=2_147_483_647)] | None = None


class ScenarioOut(Out):
    id: uuid.UUID
    term_id: uuid.UUID
    name: str
    description: str | None
    profile_codes: list[str]
    scope_department_ids: list[uuid.UUID]
    base_solution_id: uuid.UUID | None
    minimize_changes: bool
    solver_mode: str
    time_limit_seconds: int
    seed: int
    created_by_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int


# ── runs ───────────────────────────────────────────────────────────────


class RunSettingsOut(Out):
    name: str | None = None
    mode: str
    time_limit_seconds: int
    seed: int
    profiles: list[str]
    scope_department_ids: list[str]
    pinned_sessions: int
    minimize_changes: bool


class RunOut(Out):
    id: uuid.UUID
    term_id: uuid.UUID
    scenario_id: uuid.UUID | None
    source_solution_id: uuid.UUID | None
    snapshot_id: uuid.UUID
    kind: str
    status: str
    phase: str | None
    progress: dict[str, Any]
    settings: RunSettingsOut
    requested_by_id: uuid.UUID | None
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested: bool
    attempts: int
    error_code: str | None
    error_message: str | None
    result: dict[str, Any]
    app_version: str
    solver_version: str

    @model_validator(mode="before")
    @classmethod
    def _settings(cls, value: Any) -> Any:
        config = getattr(value, "config", None)
        if config is None:
            return value
        fields = {name: getattr(value, name) for name in cls.model_fields if hasattr(value, name)}
        fields["settings"] = {
            "name": config.get("name"),
            "mode": config["mode"],
            "time_limit_seconds": config["time_limit_seconds"],
            "seed": config["seed"],
            "profiles": [p["code"] for p in config.get("profiles", [])],
            "scope_department_ids": config.get("scope_department_ids", []),
            "pinned_sessions": len(config.get("pins") or {}),
            "minimize_changes": config.get("reference") is not None,
        }
        return fields


class RunEventOut(Out):
    id: int
    occurred_at: datetime
    kind: str
    payload: dict[str, Any]


class SolutionRunIn(Schema):
    time_limit_seconds: Seconds = 60
    mode: Mode = "fastest"
    scope_department_ids: list[uuid.UUID] = []


class DiagnosisIn(Schema):
    time_limit_seconds: Seconds = 60


class ChangeOut(Out):
    kind: str
    cost: int
    units: int
    sessions: list[str]
    slots: list[tuple[int, int]]
    subject_kind: str | None
    subject_id: str | None
    message: str


class DiagnosisOut(Out):
    run_id: uuid.UUID
    status: str
    complete: bool
    unscheduled: list[str]
    total_cost: int
    changes: list[ChangeOut]


# ── solutions ──────────────────────────────────────────────────────────


class SolutionOut(Out):
    id: uuid.UUID
    term_id: uuid.UUID
    snapshot_id: uuid.UUID
    run_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    name: str
    origin: str
    profile_code: str | None
    status: str
    is_complete: bool
    hard_violation_count: int
    tiers: list[int]
    objective_values: dict[str, int]
    evaluated_at: datetime | None
    created_by_id: uuid.UUID | None
    submitted_at: datetime | None
    approved_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    @model_validator(mode="before")
    @classmethod
    def _metrics(cls, value: Any) -> Any:
        evaluation = getattr(value, "evaluation", None)
        if evaluation is None:
            return value
        fields = {name: getattr(value, name) for name in cls.model_fields if hasattr(value, name)}
        fields["tiers"] = evaluation.get("tiers", [])
        fields["objective_values"] = evaluation.get("objective_values", {})
        return fields


class ViolationOut(Out):
    code: str
    message: str
    sessions: list[str]
    slots: list[tuple[int, int]]
    rule_id: str | None
    subject_kind: str | None
    subject_id: str | None


class EvaluationOut(Out):
    tiers: list[int]
    objective_values: dict[str, int]
    rule_values: dict[str, int]
    unscheduled: list[str]
    violations: list[ViolationOut]
    contributors: dict[str, list[tuple[str, int]]]
    solver_agrees: bool | None = None


class GridDayOut(Out):
    index: int
    weekday: int


class GridPeriodOut(Out):
    index: int
    label: str
    start: str
    end: str


class GridOut(Out):
    days: list[GridDayOut]
    periods: list[GridPeriodOut]
    closed: list[tuple[int, int]]


class TimetableSessionOut(Out):
    id: str
    activity_id: str
    occurrence: int
    course_code: str
    course_title: str
    type: str
    type_name: str
    label: str | None
    groups: list[str]
    instructors: list[str]
    duration: int
    online: bool
    day: int | None
    period: int | None
    room_id: str | None
    locked: bool


class GroupRefOut(Out):
    code: str
    name: str
    size: int
    parent_id: str | None


class InstructorRefOut(Out):
    code: str
    name: str


class RoomRefOut(Out):
    code: str
    name: str | None
    capacity: int


class ResourcesOut(Out):
    groups: dict[str, GroupRefOut]
    instructors: dict[str, InstructorRefOut]
    rooms: dict[str, RoomRefOut]


class TimetableOut(Out):
    grid: GridOut
    sessions: list[TimetableSessionOut]
    unscheduled: list[str]
    resources: ResourcesOut
    violations: list[ViolationOut]


class CompareRowOut(Out):
    id: str
    name: str
    profile_code: str | None
    status: str
    complete: bool
    hard_violations: int
    unscheduled_periods: int
    tiers: list[int]
    objective_values: dict[str, int]
    rule_values: dict[str, int]


class DifferenceOut(Out):
    id: str
    moved: int
    room_changes: int
    added: int
    removed: int


class CompareOut(Out):
    profile: str
    solutions: list[CompareRowOut]
    ranking: list[str]
    dominance: list[tuple[str, str]]
    """Pairs ``[a, b]``: ``a`` is at least as good as ``b`` on every measure and better on one."""
    differences: list[DifferenceOut]
    """Placements that differ from the first timetable compared."""


class FreePlaceOut(Out):
    day: int
    period: int
    room_id: str | None


class ObstacleOut(Out):
    code: str
    windows: int
    sessions: list[str]
    rule_id: str | None
    subject_kind: str | None
    subject_id: str | None
    message: str


class ExplanationOut(Out):
    session_id: str
    windows: int
    rooms: int
    free: list[FreePlaceOut]
    obstacles: list[ObstacleOut]
    room_problems: dict[str, int]
    summary: str


# ── editing ────────────────────────────────────────────────────────────


class MoveIn(Schema):
    session_id: uuid.UUID
    day: Annotated[int, Field(ge=0, le=6)] | None
    """``null`` (with ``period``) takes the session out of the timetable."""
    period: Annotated[int, Field(ge=0, le=47)] | None
    room_id: uuid.UUID | None = None


class MovesIn(Schema):
    version: int
    moves: Annotated[list[MoveIn], Field(min_length=1, max_length=50)]
    reason: LongText | None = None
    force: bool = False
    """Apply even if hard requirements break (the draft cannot be submitted until fixed)."""
    dry_run: bool = False


class MovePreviewOut(Out):
    valid: bool
    introduced: list[ViolationOut]
    resolved: list[ViolationOut]
    tiers_before: list[int]
    tiers_after: list[int]
    objective_deltas: dict[str, int]
    rule_deltas: dict[str, int]
    hard_violations_after: int
    complete_after: bool


class MovesOut(Out):
    applied: bool
    preview: MovePreviewOut
    solution: SolutionOut | None


class PlaceOut(Out):
    day: int
    period: int
    room_id: str | None


class ValidOptionOut(PlaceOut):
    is_current: bool
    tier_deltas: list[int]
    objective_deltas: dict[str, int]


class BlockedOptionOut(PlaceOut):
    violations: list[ViolationOut]


class SuggestionsOut(Out):
    session_id: str
    current: PlaceOut | None
    valid: list[ValidOptionOut]
    blocked: list[BlockedOptionOut]
    valid_count: int
    blocked_count: int


class LocksIn(Schema):
    version: int
    session_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=2000)]
    locked: bool
    reason: LongText | None = None


class ChangeLogOut(Out):
    seq: int
    occurred_at: datetime
    actor_id: uuid.UUID | None
    actor_label: str
    kind: str
    session_id: uuid.UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    summary: str
    reason: str | None


class DuplicateIn(Schema):
    name: Name | None = None


class WorkflowIn(Schema):
    version: int
    note: LongText | None = None


class ReturnIn(Schema):
    version: int
    note: Annotated[str, Field(min_length=1, max_length=4000)]
