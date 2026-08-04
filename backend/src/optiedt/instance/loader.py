"""Load data/instance/ (13 CSVs) into an Instance.

One function per file, orchestrated by load_instance(). Conversions are
mechanical (CSV strings to the types the domain entities declare) except
for two documented corrections against what the raw files actually contain:

  - courses.csv and teacher_availability.csv encode "semester" as "S2",
    a string code, but Course.semester and Availability.semester are int.
    Parsed by stripping the leading letter: "S2" -> 2.

  - teacher_availability.csv's is_available is a plain boolean and every
    row in the reference instance is 0 (unavailable). There is no
    representation of a preferred window in this file, so this loader can
    produce AvailabilityState.UNAVAILABLE and .AVAILABLE but never
    .PREFERRED from real data. See C-12 in docs/open-questions.md — this
    is a data gap, not a bug in the loader.

students.csv is not read here. Student exists only for the examination
model (X1), which is increment 2; loading it now would be dead weight
carried through every Phase 2 solve.
"""

from __future__ import annotations

import csv
from datetime import date, time
from pathlib import Path

from optiedt.domain.entities import (
    Availability,
    ConstraintDefinition,
    Course,
    Group,
    Holiday,
    Programme,
    Promotion,
    Room,
    Session,
    Slot,
    Teacher,
)
from optiedt.domain.enums import (
    AvailabilityState,
    ConstraintKind,
    DeclarationSource,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.domain.instance import Instance

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def resolve_instance_path(configured: str) -> Path:
    """Absolute path of `data/instance/`, independent of the working directory.

    ⚠️ The configured default is `"../data/instance"`, relative to `backend/`.
    Resolving it against the CURRENT directory would make the application work
    under `uvicorn` started from `backend/` and fail under pytest started from
    the repository root - a difference that surfaces as "the instance is
    missing" rather than as a path bug. It is resolved against this file's
    location instead.

    Lives here rather than in `api/deps.py` because `services/seed.py` needs it
    too, and reaching up into the API layer for it would invert the module map
    for the sake of one path.
    """
    path = Path(configured)
    return path if path.is_absolute() else (_BACKEND_ROOT / path).resolve()


def _rows(path: Path, filename: str) -> list[dict[str, str]]:
    with (path / filename).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _flag(value: str) -> bool:
    """ "0"/"1" (also "false"/"true") -> bool."""
    return value.strip().lower() in {"1", "true"}


def _optional(value: str) -> str | None:
    """Empty string, or the XHSTT "no reference" marker "-", -> None."""
    v = value.strip()
    return None if v in ("", "-") else v


def _semester(value: str) -> int:
    """ "S2" -> 2. See module docstring: the CSVs encode a string code,
    the domain entities declare an int."""
    v = value.strip()
    return int(v[1:]) if v and v[0] in "Ss" else int(v)


def _load_programmes(path: Path) -> tuple[Programme, ...]:
    return tuple(
        Programme(
            id=r["programme_id"],
            code=r["code"],
            label=r["label"],
            degree_cycle=r["degree_cycle"],
            department=r["department"],
        )
        for r in _rows(path, "programmes.csv")
    )


def _load_promotions(path: Path) -> tuple[Promotion, ...]:
    return tuple(
        Promotion(
            id=r["promotion_id"],
            programme=r["programme_id"],
            level=r["level"],
            academic_year=r["academic_year"],
            student_count=int(r["n_students"]),
        )
        for r in _rows(path, "promotions.csv")
    )


def _load_groups(path: Path) -> tuple[Group, ...]:
    return tuple(
        Group(
            id=r["group_id"],
            promotion=r["promotion_id"],
            parent_group=_optional(r["parent_group_id"]),
            level=GroupLevel(r["group_type"]),
            label=r["label"],
            size=int(r["n_students"]),
        )
        for r in _rows(path, "groups.csv")
    )


def _load_teachers(path: Path) -> tuple[Teacher, ...]:
    return tuple(
        Teacher(
            id=r["teacher_id"],
            department=r["department"],
            rank=TeacherRank(r["rank"]),
            max_hours_per_week=int(r["max_hours_per_week"]),
        )
        for r in _rows(path, "teachers.csv")
    )


def _load_courses(path: Path) -> tuple[Course, ...]:
    return tuple(
        Course(
            id=r["course_id"],
            code=r["code"],
            department=r["department"],
            programme=r["programme_id"],
            level=r["level"],
            semester=_semester(r["semester"]),
            credits=int(r["credits"]),
        )
        for r in _rows(path, "courses.csv")
    )


def _load_sessions(path: Path) -> tuple[Session, ...]:
    return tuple(
        Session(
            id=r["session_id"],
            course=r["course_id"],
            group=r["group_id"],
            teacher=r["teacher_id"],
            type=SessionType(r["session_type"]),
            duration_periods=int(r["duration_periods"]),
            occurrences_per_week=int(r["occurrences_per_week"]),
            required_room_type=RoomType(r["required_room_type"]),
            locked=_flag(r["is_locked"]),
        )
        for r in _rows(path, "sessions.csv")
    )


def _load_rooms(path: Path) -> tuple[Room, ...]:
    rooms = []
    for r in _rows(path, "rooms.csv"):
        equipment = tuple(
            name
            for name, present in (
                ("projector", r.get("has_projector", "0")),
                ("computers", r.get("has_computers", "0")),
            )
            if _flag(present)
        )
        rooms.append(
            Room(
                id=r["room_id"],
                building=r["building"],
                code=r["code"],
                capacity=int(r["capacity"]),
                type=RoomType(r["room_type"]),
                equipment=equipment,
            )
        )
    return tuple(rooms)


def _load_slots(path: Path) -> tuple[Slot, ...]:
    slots = []
    for r in _rows(path, "slots.csv"):
        index = int(r["slot_id"])
        day_index = int(r["day_index"])
        period_index = int(r["period_index"])
        slots.append(
            Slot(
                index=index,
                day_index=day_index,
                period_index=period_index,
                start_hour=time.fromisoformat(r["start_time"]),
                end_hour=time.fromisoformat(r["end_time"]),
                is_open=_flag(r["is_open"]),
            )
        )
    return tuple(slots)


def _load_availability(path: Path) -> tuple[Availability, ...]:
    return tuple(
        Availability(
            teacher=r["teacher_id"],
            slot=int(r["slot_id"]),
            state=(
                AvailabilityState.AVAILABLE
                if _flag(r["is_available"])
                else AvailabilityState.UNAVAILABLE
            ),
            semester=_semester(r["semester"]),
            source=DeclarationSource(r["source"]),
        )
        for r in _rows(path, "teacher_availability.csv")
    )


def _load_holidays(path: Path) -> tuple[Holiday, ...]:
    return tuple(
        Holiday(
            date=date.fromisoformat(r["holiday_date"]),
            label=r["label"],
            lunar=_flag(r["is_islamic"]),
            approximate=_flag(r["is_approximate"]),
            blocking=_flag(r["blocks_scheduling"]),
        )
        for r in _rows(path, "holidays.csv")
    )


def _load_calendar_config(path: Path) -> dict[str, str]:
    return {r["key"]: r["value"] for r in _rows(path, "calendar_config.csv")}


def _load_constraints(path: Path) -> tuple[ConstraintDefinition, ...]:
    return tuple(
        ConstraintDefinition(
            code=r["code"],
            name=r["name"],
            kind=ConstraintKind(r["kind"]),
            default_weight=float(r["default_weight"]) if r["default_weight"].strip() else 0.0,
            xhstt_reference=_optional(r["xhstt_ref"]),
        )
        for r in _rows(path, "constraint_catalogue.csv")
    )


def load_instance(path: Path | str) -> Instance:
    """Read the 13 CSVs at ``path`` (data/instance/, or a copy of it for a
    test fixture) into a populated Instance.

    Raises FileNotFoundError with the offending filename if a CSV is
    missing, rather than a bare csv module error, since a missing file
    here means the instance is incomplete and that should be obvious.
    """
    root = Path(path)
    for name in (
        "programmes.csv",
        "promotions.csv",
        "groups.csv",
        "teachers.csv",
        "courses.csv",
        "sessions.csv",
        "rooms.csv",
        "slots.csv",
        "teacher_availability.csv",
        "holidays.csv",
        "calendar_config.csv",
        "constraint_catalogue.csv",
    ):
        if not (root / name).is_file():
            raise FileNotFoundError(f"instance file missing: {root / name}")

    return Instance(
        programmes=_load_programmes(root),
        promotions=_load_promotions(root),
        groups=_load_groups(root),
        teachers=_load_teachers(root),
        courses=_load_courses(root),
        sessions=_load_sessions(root),
        rooms=_load_rooms(root),
        slots=_load_slots(root),
        availability=_load_availability(root),
        holidays=_load_holidays(root),
        calendar_config=_load_calendar_config(root),
        constraints=_load_constraints(root),
    )
