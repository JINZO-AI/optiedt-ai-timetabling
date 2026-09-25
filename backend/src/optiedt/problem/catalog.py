"""Catalogue of configurable rule types and built-in objectives.

These are definitions only — codes, parameters, scopes and defaults. The solver and the
evaluator each implement the semantics independently (ADR 0009).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ScopeKind(StrEnum):
    RESOURCES = "resources"
    """Instructors and/or student groups; the rule applies to each target separately."""
    TARGETS = "targets"
    """Resources and/or activities; the rule applies to each target separately."""
    ACTIVITY_SET = "activity_set"
    """Two or more activities; the rule relates them to each other."""
    ACTIVITY_PAIR = "activity_pair"
    """An ordered pair of activities."""
    ACTIVITIES = "activities"
    """One or more activities; the rule applies to each separately."""


class _Params(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LimitParams(_Params):
    limit: int = Field(ge=1, le=24)


class DaysLimitParams(_Params):
    limit: int = Field(ge=1, le=7)


class BreakParams(_Params):
    period_ids: list[uuid.UUID] = Field(min_length=1, max_length=24)
    min_free: int = Field(default=1, ge=1, le=24)

    @model_validator(mode="after")
    def _fits(self) -> BreakParams:
        if self.min_free > len(self.period_ids):
            raise ValueError("min_free cannot exceed the number of periods in the window")
        return self


class SlotRef(_Params):
    weekday: int = Field(ge=0, le=6)
    period_id: uuid.UUID


class SlotsParams(_Params):
    slots: list[SlotRef] = Field(min_length=1, max_length=200)


class PeriodParams(_Params):
    period_id: uuid.UUID


class MinDaysParams(_Params):
    days: int = Field(ge=1, le=6)


class NoParams(_Params):
    pass


class _ResourceTargets(_Params):
    all_instructors: bool = False
    all_groups: bool = False
    instructor_ids: list[uuid.UUID] = Field(default_factory=list, max_length=2000)
    group_ids: list[uuid.UUID] = Field(default_factory=list, max_length=2000)
    department_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    """Instructors of these departments (and their sub-departments)."""

    def _has_resources(self) -> bool:
        return bool(
            self.all_instructors
            or self.all_groups
            or self.instructor_ids
            or self.group_ids
            or self.department_ids
        )


class ResourceScope(_ResourceTargets):
    @model_validator(mode="after")
    def _not_empty(self) -> ResourceScope:
        if not self._has_resources():
            raise ValueError("choose at least one instructor, group or department")
        return self


class TargetScope(_ResourceTargets):
    activity_ids: list[uuid.UUID] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def _not_empty(self) -> TargetScope:
        if not (self._has_resources() or self.activity_ids):
            raise ValueError("choose at least one instructor, group, department or activity")
        return self


class ActivitySetScope(_Params):
    activity_ids: list[uuid.UUID] = Field(min_length=2, max_length=200)

    @model_validator(mode="after")
    def _distinct(self) -> ActivitySetScope:
        if len(set(self.activity_ids)) != len(self.activity_ids):
            raise ValueError("each activity may be listed once")
        return self


class ActivitiesScope(_Params):
    activity_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def _distinct(self) -> ActivitiesScope:
        if len(set(self.activity_ids)) != len(self.activity_ids):
            raise ValueError("each activity may be listed once")
        return self


class ActivityPairScope(_Params):
    first_activity_id: uuid.UUID
    second_activity_id: uuid.UUID

    @model_validator(mode="after")
    def _distinct(self) -> ActivityPairScope:
        if self.first_activity_id == self.second_activity_id:
            raise ValueError("the two activities must differ")
        return self


SCOPE_MODELS: dict[ScopeKind, type[_Params]] = {
    ScopeKind.RESOURCES: ResourceScope,
    ScopeKind.TARGETS: TargetScope,
    ScopeKind.ACTIVITY_SET: ActivitySetScope,
    ScopeKind.ACTIVITY_PAIR: ActivityPairScope,
    ScopeKind.ACTIVITIES: ActivitiesScope,
}


@dataclass(frozen=True, slots=True)
class RuleType:
    code: str
    name: str
    description: str
    scope: ScopeKind
    params: type[_Params]
    unit: str
    """What one unit of soft violation counts."""


RULE_TYPES: dict[str, RuleType] = {
    rule.code: rule
    for rule in (
        RuleType(
            "max_periods_per_day",
            "Maximum periods per day",
            "Limits the number of occupied periods per day.",
            ScopeKind.RESOURCES,
            LimitParams,
            "periods above the limit",
        ),
        RuleType(
            "max_consecutive_periods",
            "Maximum consecutive periods",
            "Limits uninterrupted teaching; a free period or a break resets the count.",
            ScopeKind.RESOURCES,
            LimitParams,
            "periods above the limit",
        ),
        RuleType(
            "max_days_per_week",
            "Maximum days per week",
            "Limits the number of days with at least one session.",
            ScopeKind.RESOURCES,
            DaysLimitParams,
            "days above the limit",
        ),
        RuleType(
            "break_in_window",
            "Break within a window",
            "Keeps a number of periods free in a window each day, such as a lunch break.",
            ScopeKind.RESOURCES,
            BreakParams,
            "missing free periods",
        ),
        RuleType(
            "avoid_slots",
            "Avoid slots",
            "Keeps sessions out of the listed slots.",
            ScopeKind.TARGETS,
            SlotsParams,
            "occupied periods in avoided slots",
        ),
        RuleType(
            "earliest_start",
            "Earliest start",
            "No session before the given period on any day.",
            ScopeKind.TARGETS,
            PeriodParams,
            "occupied periods before the earliest start",
        ),
        RuleType(
            "latest_end",
            "Latest end",
            "No session after the given period on any day.",
            ScopeKind.TARGETS,
            PeriodParams,
            "occupied periods after the latest end",
        ),
        RuleType(
            "min_days_between",
            "Minimum days between sessions",
            "Occurrences of each activity are at least this many days apart.",
            ScopeKind.ACTIVITIES,
            MinDaysParams,
            "occurrence pairs too close",
        ),
        RuleType(
            "not_overlapping",
            "Not at the same time",
            "The listed activities never overlap in time.",
            ScopeKind.ACTIVITY_SET,
            NoParams,
            "overlapping periods",
        ),
        RuleType(
            "same_start",
            "Same start time",
            "Occurrence k of each listed activity starts in the same slot.",
            ScopeKind.ACTIVITY_SET,
            NoParams,
            "occurrences not aligned",
        ),
        RuleType(
            "same_day",
            "Same day",
            "Occurrence k of each listed activity is on the same day.",
            ScopeKind.ACTIVITY_SET,
            NoParams,
            "occurrences not on the same day",
        ),
        RuleType(
            "different_days",
            "Different days",
            "No two listed activities take place on the same day.",
            ScopeKind.ACTIVITY_SET,
            NoParams,
            "same-day pairs",
        ),
        RuleType(
            "precedence",
            "Precedence",
            "Occurrence k of the first activity ends before occurrence k of the second starts.",
            ScopeKind.ACTIVITY_PAIR,
            NoParams,
            "occurrences out of order",
        ),
        RuleType(
            "consecutive",
            "Immediately after",
            "Occurrence k of the second activity starts right after occurrence k of the first, "
            "on the same day.",
            ScopeKind.ACTIVITY_PAIR,
            NoParams,
            "occurrences not consecutive",
        ),
        RuleType(
            "campus_travel",
            "Campus travel time",
            "Sessions in adjacent periods are on campuses reachable in the time between them.",
            ScopeKind.RESOURCES,
            NoParams,
            "transitions without enough travel time",
        ),
    )
}


class RuleDefinitionError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def validate_rule(
    rule_type: str, params: dict[str, Any], scope: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns normalised (params, scope) or raises ``RuleDefinitionError``."""
    definition = RULE_TYPES.get(rule_type)
    if definition is None:
        raise RuleDefinitionError("rule_type", f"Unknown rule type {rule_type!r}.")
    try:
        parsed_params = definition.params.model_validate(params)
    except ValidationError as error:
        raise RuleDefinitionError("params", _first_error(error)) from error
    try:
        parsed_scope = SCOPE_MODELS[definition.scope].model_validate(scope)
    except ValidationError as error:
        raise RuleDefinitionError("scope", _first_error(error)) from error
    return parsed_params.model_dump(mode="json"), parsed_scope.model_dump(mode="json")


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    message = str(first.get("msg", "invalid value"))
    return f"{location}: {message}" if location else message


# ── objectives ─────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ObjectiveType:
    code: str
    name: str
    description: str
    unit: str


OBJECTIVES: dict[str, ObjectiveType] = {
    o.code: o
    for o in (
        ObjectiveType(
            "student_idle",
            "Student idle time",
            "Free periods between a student group's first and last session of a day.",
            "idle periods",
        ),
        ObjectiveType(
            "instructor_idle",
            "Instructor idle time",
            "Free periods between an instructor's first and last session of a day.",
            "idle periods",
        ),
        ObjectiveType(
            "instructor_undesirable",
            "Instructor undesirable periods",
            "Teaching in periods an instructor marked as undesirable.",
            "periods",
        ),
        ObjectiveType(
            "instructor_preferred",
            "Instructor preferred periods",
            "Teaching outside the periods an instructor marked as preferred.",
            "periods",
        ),
        ObjectiveType(
            "undesirable_slots",
            "Undesirable slots",
            "Sessions in slots the institution penalises, weighted by penalty level.",
            "weighted periods",
        ),
        ObjectiveType(
            "room_fit",
            "Room size fit",
            "Empty seats in the rooms used, per period.",
            "empty seat-periods",
        ),
        ObjectiveType(
            "room_preferences",
            "Room preferences",
            "Sessions outside their activity's preferred rooms or in avoided rooms.",
            "sessions",
        ),
        ObjectiveType(
            "room_stability",
            "Room stability",
            "Additional rooms used by the occurrences of one activity.",
            "extra rooms",
        ),
        ObjectiveType(
            "start_consistency",
            "Consistent start times",
            "Additional start periods used by the occurrences of one activity.",
            "extra start periods",
        ),
        ObjectiveType(
            "instructor_days",
            "Instructor days on campus",
            "Teaching days beyond the minimum an instructor's load requires.",
            "extra days",
        ),
        ObjectiveType(
            "stability",
            "Changes from the reference",
            "Occurrences moved in time (counted three times) or to another room, relative "
            "to the reference solution.",
            "weighted changes",
        ),
    )
}

UNSCHEDULED = "unscheduled"
STABILITY_TIME_WEIGHT = 3
STABILITY_ROOM_WEIGHT = 1
MAX_TIER = 5


def _profile(**entries: tuple[int, int]) -> dict[str, dict[str, Any]]:
    return {
        code: {"tier": tier, "weight": weight, "enabled": True}
        for code, (tier, weight) in entries.items()
    }


BUILT_IN_PROFILES: tuple[tuple[str, str, str, dict[str, dict[str, Any]]], ...] = (
    (
        "balanced",
        "Balanced",
        "Instructor wishes first, then compact days for students and staff, then rooms.",
        _profile(
            instructor_undesirable=(1, 1),
            student_idle=(2, 2),
            instructor_idle=(2, 1),
            instructor_days=(2, 1),
            undesirable_slots=(2, 1),
            instructor_preferred=(3, 1),
            room_preferences=(3, 2),
            room_stability=(3, 1),
            start_consistency=(3, 1),
            room_fit=(4, 1),
        ),
    ),
    (
        "student_centred",
        "Student-centred",
        "Compact student days first, then instructor wishes, then rooms.",
        _profile(
            student_idle=(1, 1),
            instructor_undesirable=(2, 2),
            undesirable_slots=(2, 1),
            instructor_idle=(3, 1),
            instructor_days=(3, 1),
            start_consistency=(3, 1),
            instructor_preferred=(3, 1),
            room_preferences=(4, 2),
            room_stability=(4, 1),
            room_fit=(5, 1),
        ),
    ),
    (
        "instructor_centred",
        "Instructor-centred",
        "Instructor wishes and compact teaching days first, then students, then rooms.",
        _profile(
            instructor_undesirable=(1, 1),
            instructor_idle=(2, 2),
            instructor_days=(2, 2),
            instructor_preferred=(2, 1),
            student_idle=(3, 1),
            undesirable_slots=(3, 1),
            start_consistency=(3, 1),
            room_preferences=(4, 2),
            room_stability=(4, 1),
            room_fit=(5, 1),
        ),
    ),
    (
        "room_efficient",
        "Room-efficient",
        "Rooms matched to group sizes first, keeping instructor wishes ahead of comfort.",
        _profile(
            instructor_undesirable=(1, 1),
            room_fit=(2, 1),
            room_preferences=(3, 2),
            room_stability=(3, 1),
            student_idle=(4, 2),
            instructor_idle=(4, 1),
            instructor_days=(4, 1),
            undesirable_slots=(4, 1),
            start_consistency=(4, 1),
            instructor_preferred=(4, 1),
        ),
    ),
)


class ObjectiveSetting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: int = Field(ge=1, le=MAX_TIER)
    weight: int = Field(ge=1, le=1000)
    enabled: bool = True


def validate_objectives(objectives: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for code, setting in objectives.items():
        if code not in OBJECTIVES or code == "stability":
            raise RuleDefinitionError("objectives", f"Unknown or reserved objective {code!r}.")
        try:
            result[code] = ObjectiveSetting.model_validate(setting).model_dump()
        except ValidationError as error:
            raise RuleDefinitionError(f"objectives.{code}", _first_error(error)) from error
    return result
