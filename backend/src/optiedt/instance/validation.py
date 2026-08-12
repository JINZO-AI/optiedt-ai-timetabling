"""FR-1 — verify a supplied department dataset, then build an Instance from it.

    SRS §3.2, Table 4. FR-1. Data management (the supervisor's own words):
      Input       Files or forms validated by the server
      Processing  Verification of the types and of the references, then
                  recording
      Output      Entities recorded and report of the rejected lines

This module is the "verification of the types and of the references" half. It
takes the supplied files as text and returns either an Instance or a report of
every rejected line — never both, and never a partial Instance.

⚠️ **It collects; it does not stop at the first fault.** A person fixing a
department's data needs the whole list, and an importer that reported one bad
row per attempt would turn a hundred-row correction into a hundred round trips.

⚠️ **`constraint_catalogue.csv` is NOT part of a department dataset and is not
accepted here.** The catalogue is the list of rules the *software* supports -
H1 to H12 and the soft criteria — not data the institution owns. Accepting it
would let an upload delete a hard constraint, which ADR-003 and invariant 7
forbid and `acceptance/test_fr09` asserts against. It stays with the
application, read from `data/instance/` by `optiedt.instance.loader`.

⚠️ **`students.csv` is not accepted either**, and since Phase 13 the reason has
changed rather than disappeared. `Instance` no longer excludes `Student` — the
loader reads the roster for the examination model (X1). What stays true is that
the roster is **not part of the eleven-file contract a department supplies**:
SRS §3.2 Table 19 lists students among FR-20's inputs but SRS §4.1 names no
form for them, and admitting a twelfth file here would be the examination-data
upload system FR-1 was deliberately scoped not to become. A supplied dataset
therefore carries no roster, `Instance.students` is empty, and an examination
session on it is **refused with that reason** rather than solved against zero
candidates.

**What this module deliberately does NOT check**, so that one question keeps one
answer: the promotion → TD → TP *level* rule. That is FR-12's
`preanalysis.verifications.GroupHierarchy`, which runs at stage 1 of every run
and names the resource concerned. A group whose parent is the wrong level is a
structural risk the pre-analysis reports; a group whose parent does not exist is
a broken *reference*, which is what this module is for.

**Cycles are the exception, and they are checked here** — not for tidiness but
because `solver/constraints/overlap.py::_ancestor_chain` walks the chain with
`while current is not None` and a failing pre-analysis does **not** stop a run
(`tasks/executor.py::_preanalyse`). A cyclic hierarchy that reached the solver
would hang the run thread rather than fail it. A cycle is also a defect of the
reference graph itself, which puts it inside this module's remit either way.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import date, time

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
    DeclarationSource,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.domain.instance import Instance

PROGRAMMES = "programmes.csv"
PROMOTIONS = "promotions.csv"
GROUPS = "groups.csv"
TEACHERS = "teachers.csv"
COURSES = "courses.csv"
SESSIONS = "sessions.csv"
ROOMS = "rooms.csv"
SLOTS = "slots.csv"
AVAILABILITY = "teacher_availability.csv"
HOLIDAYS = "holidays.csv"
CALENDAR_CONFIG = "calendar_config.csv"

DEPARTMENT_FILES: tuple[str, ...] = (
    PROGRAMMES,
    PROMOTIONS,
    GROUPS,
    TEACHERS,
    COURSES,
    SESSIONS,
    ROOMS,
    SLOTS,
    AVAILABILITY,
    HOLIDAYS,
    CALENDAR_CONFIG,
)
"""The eleven files a department dataset consists of.

⚠️ **Eleven, not the loader's twelve.** `constraint_catalogue.csv` is the
software's rule catalogue and is excluded — see the module docstring. The order
is the order rejections are reported in, which is dependency order: a file is
listed after everything it refers to.
"""

_REQUIRED_COLUMNS: Mapping[str, tuple[str, ...]] = {
    PROGRAMMES: ("programme_id", "code", "label", "degree_cycle", "department"),
    PROMOTIONS: ("promotion_id", "programme_id", "level", "academic_year", "n_students"),
    GROUPS: ("group_id", "promotion_id", "parent_group_id", "group_type", "label", "n_students"),
    TEACHERS: ("teacher_id", "department", "rank", "max_hours_per_week"),
    COURSES: ("course_id", "code", "department", "programme_id", "level", "semester", "credits"),
    SESSIONS: (
        "session_id",
        "course_id",
        "group_id",
        "teacher_id",
        "session_type",
        "duration_periods",
        "occurrences_per_week",
        "required_room_type",
        "is_locked",
    ),
    ROOMS: ("room_id", "building", "code", "capacity", "room_type"),
    SLOTS: ("slot_id", "day_index", "period_index", "start_time", "end_time", "is_open"),
    AVAILABILITY: ("teacher_id", "slot_id", "is_available", "semester", "source"),
    HOLIDAYS: (
        "holiday_date",
        "label",
        "is_islamic",
        "is_approximate",
        "blocks_scheduling",
    ),
    CALENDAR_CONFIG: ("key", "value"),
}
"""Columns each file must carry.

`rooms.csv`'s `has_projector` and `has_computers` are absent on purpose: the
loader reads them with `.get(..., "0")`, so a dataset without them is complete
rather than defective, and requiring them here would reject a file the
application can read.
"""


@dataclass(frozen=True, slots=True)
class RejectedLine:
    """One reason one line could not be accepted.

    `line` is the **physical** line number in the file, header included, so it
    matches what a spreadsheet or a text editor shows. `None` means the fault is
    the file as a whole — missing, empty, or without the columns it needs.
    """

    file: str
    line: int | None
    reason: str
    field: str | None = None
    value: str | None = None

    def describe(self) -> str:
        where = f"{self.file}" if self.line is None else f"{self.file}:{self.line}"
        field = f" [{self.field}]" if self.field else ""
        return f"{where}{field} — {self.reason}"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Either an instance or a report. Never a partial instance.

    ⚠️ **`instance` is `None` whenever `rejected` is non-empty**, and that
    coupling is the atomicity rule at its source: a caller cannot record
    "the good rows" because this type never offers them. See
    `services/dataset.py` for the persistence half of the same rule.
    """

    instance: Instance | None
    rejected: tuple[RejectedLine, ...]
    references_checked: bool = False
    """Whether the reference stage ran.

    ⚠️ It does not run while any line has failed to parse — a rejected line
    takes its identifier with it, so every reference to that entity would be
    reported as unknown, which is one defect producing two reports. Carried out
    of this module so the interface can say *"fix these, then the references are
    examined"* instead of leaving a user to discover a second round.
    """

    @property
    def accepted(self) -> bool:
        return self.instance is not None


class _Collector:
    """Accumulates rejections for one file while its rows are parsed."""

    def __init__(self, file: str) -> None:
        self.file = file
        self.rejected: list[RejectedLine] = []

    def reject(
        self, line: int | None, reason: str, field: str | None = None, value: str | None = None
    ) -> None:
        self.rejected.append(
            RejectedLine(file=self.file, line=line, reason=reason, field=field, value=value)
        )

    @property
    def clean(self) -> bool:
        return not self.rejected


@dataclass(frozen=True, slots=True)
class _Row:
    line: int
    values: Mapping[str, str]


def _read_rows(text: str, file: str, collector: _Collector) -> list[_Row]:
    """Physical rows of a CSV, with their line numbers and their columns checked.

    Returns an empty list — and records a file-level rejection — when the file
    is empty or is missing a column the entities need. Continuing past a missing
    column would produce one rejection per row for a fault that is one fault.
    """
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        collector.reject(None, "the file is empty; a header line is required")
        return []

    # A UTF-8 BOM survives `str` decoding and would make the first column name
    # "﻿programme_id". The loader strips it by opening with utf-8-sig; a
    # file arriving as text has to be stripped here or every column check on the
    # first column fails for an invisible reason.
    if header and header[0].startswith("﻿"):
        header = [header[0].lstrip("﻿"), *header[1:]]
    header = [name.strip() for name in header]

    missing = [name for name in _REQUIRED_COLUMNS[file] if name not in header]
    if missing:
        collector.reject(1, f"missing required column(s): {', '.join(missing)}")
        return []

    duplicated = sorted({name for name in header if header.count(name) > 1})
    if duplicated:
        collector.reject(1, f"column(s) declared more than once: {', '.join(duplicated)}")
        return []

    rows: list[_Row] = []
    for raw in reader:
        line = reader.line_num
        if not any(cell.strip() for cell in raw):
            # A trailing newline, or a blank separator line. Not a fault.
            continue
        if len(raw) != len(header):
            collector.reject(
                line,
                f"the line has {len(raw)} field(s) where the header declares {len(header)}",
            )
            continue
        rows.append(_Row(line=line, values=dict(zip(header, raw, strict=True))))
    return rows


# ── Field readers ──────────────────────────────────────────────────────
#
# Each returns None and records a rejection rather than raising, so one bad
# field costs one line of the report instead of the whole import.


def _text(row: _Row, field: str, collector: _Collector, *, required: bool = True) -> str | None:
    value = row.values[field].strip()
    if not value and required:
        collector.reject(row.line, "a value is required", field=field, value=row.values[field])
        return None
    return value


def _integer(
    row: _Row, field: str, collector: _Collector, *, minimum: int | None = None
) -> int | None:
    raw = row.values[field].strip()
    try:
        value = int(raw)
    except ValueError:
        collector.reject(row.line, "expected a whole number", field=field, value=raw)
        return None
    if minimum is not None and value < minimum:
        collector.reject(row.line, f"expected at least {minimum}", field=field, value=raw)
        return None
    return value


def _boolean(row: _Row, field: str, collector: _Collector) -> bool | None:
    """The loader's convention: "0"/"1", also "false"/"true". Nothing else.

    Anything else is refused rather than read as false — `_flag` in the loader
    treats every unrecognised string as false, which is right for files this
    repository generates and wrong for a file somebody typed.
    """
    raw = row.values[field].strip().lower()
    if raw in {"1", "true"}:
        return True
    if raw in {"0", "false"}:
        return False
    collector.reject(
        row.line, "expected 0, 1, true or false", field=field, value=row.values[field].strip()
    )
    return None


def _semester(row: _Row, field: str, collector: _Collector) -> int | None:
    """ "S2" -> 2, as the loader reads it. The bare integer is accepted too."""
    raw = row.values[field].strip()
    body = raw[1:] if raw[:1] in ("S", "s") else raw
    try:
        value = int(body)
    except ValueError:
        collector.reject(
            row.line, 'expected a semester such as "S2" or "2"', field=field, value=raw
        )
        return None
    if value < 1:
        collector.reject(row.line, "a semester is 1 or more", field=field, value=raw)
        return None
    return value


def _clock(row: _Row, field: str, collector: _Collector) -> time | None:
    raw = row.values[field].strip()
    try:
        return time.fromisoformat(raw)
    except ValueError:
        collector.reject(row.line, "expected an hour as HH:MM", field=field, value=raw)
        return None


def _calendar_date(row: _Row, field: str, collector: _Collector) -> date | None:
    raw = row.values[field].strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        collector.reject(row.line, "expected a date as YYYY-MM-DD", field=field, value=raw)
        return None


def _enum[E: str](
    row: _Row, field: str, collector: _Collector, factory: Callable[[str], E], admitted: Iterable[E]
) -> E | None:
    raw = row.values[field].strip()
    try:
        return factory(raw)
    except ValueError:
        collector.reject(
            row.line,
            f"expected one of: {', '.join(sorted(str(v) for v in admitted))}",
            field=field,
            value=raw,
        )
        return None


def _optional_reference(row: _Row, field: str) -> str | None:
    """Empty, or the XHSTT "no reference" marker "-", mean *absent*."""
    value = row.values[field].strip()
    return None if value in ("", "-") else value


def _unique[T](
    built: list[tuple[_Row, T]], identity: Callable[[T], object], field: str, collector: _Collector
) -> list[T]:
    """Drop nothing; reject every line whose identifier repeats an earlier one.

    ⚠️ The FIRST occurrence is kept clean and each later one is rejected, so the
    report names the lines a person has to go and look at rather than the one
    they typed correctly.
    """
    seen: dict[object, int] = {}
    kept: list[T] = []
    for row, entity in built:
        key = identity(entity)
        first = seen.get(key)
        if first is not None:
            collector.reject(
                row.line,
                f"duplicate identifier; already declared on line {first}",
                field=field,
                value=str(key),
            )
            continue
        seen[key] = row.line
        kept.append(entity)
    return kept


# ── One reader per file ────────────────────────────────────────────────


def _programmes(rows: list[_Row], c: _Collector) -> list[Programme]:
    built: list[tuple[_Row, Programme]] = []
    for row in rows:
        fields = [
            _text(row, "programme_id", c),
            _text(row, "code", c),
            _text(row, "label", c),
            _text(row, "degree_cycle", c),
            _text(row, "department", c),
        ]
        if any(f is None for f in fields):
            continue
        identifier, code, label, cycle, department = (str(f) for f in fields)
        built.append(
            (
                row,
                Programme(
                    id=identifier,
                    code=code,
                    label=label,
                    degree_cycle=cycle,
                    department=department,
                ),
            )
        )
    return _unique(built, lambda p: p.id, "programme_id", c)


def _promotions(rows: list[_Row], c: _Collector) -> list[Promotion]:
    built: list[tuple[_Row, Promotion]] = []
    for row in rows:
        identifier = _text(row, "promotion_id", c)
        programme = _text(row, "programme_id", c)
        level = _text(row, "level", c)
        year = _text(row, "academic_year", c)
        students = _integer(row, "n_students", c, minimum=0)
        if identifier is None or programme is None or level is None or year is None:
            continue
        if students is None:
            continue
        built.append(
            (
                row,
                Promotion(
                    id=identifier,
                    programme=programme,
                    level=level,
                    academic_year=year,
                    student_count=students,
                ),
            )
        )
    return _unique(built, lambda p: p.id, "promotion_id", c)


def _groups(rows: list[_Row], c: _Collector) -> list[Group]:
    built: list[tuple[_Row, Group]] = []
    for row in rows:
        identifier = _text(row, "group_id", c)
        promotion = _text(row, "promotion_id", c)
        level = _enum(row, "group_type", c, GroupLevel, GroupLevel)
        label = _text(row, "label", c)
        size = _integer(row, "n_students", c, minimum=0)
        if identifier is None or promotion is None or level is None or label is None:
            continue
        if size is None:
            continue
        built.append(
            (
                row,
                Group(
                    id=identifier,
                    promotion=promotion,
                    parent_group=_optional_reference(row, "parent_group_id"),
                    level=level,
                    label=label,
                    size=size,
                ),
            )
        )
    return _unique(built, lambda g: g.id, "group_id", c)


def _teachers(rows: list[_Row], c: _Collector) -> list[Teacher]:
    built: list[tuple[_Row, Teacher]] = []
    for row in rows:
        identifier = _text(row, "teacher_id", c)
        department = _text(row, "department", c)
        rank = _enum(row, "rank", c, TeacherRank, TeacherRank)
        hours = _integer(row, "max_hours_per_week", c, minimum=1)
        if identifier is None or department is None or rank is None or hours is None:
            continue
        built.append(
            (
                row,
                Teacher(id=identifier, department=department, rank=rank, max_hours_per_week=hours),
            )
        )
    return _unique(built, lambda t: t.id, "teacher_id", c)


def _courses(rows: list[_Row], c: _Collector) -> list[Course]:
    built: list[tuple[_Row, Course]] = []
    for row in rows:
        identifier = _text(row, "course_id", c)
        code = _text(row, "code", c)
        department = _text(row, "department", c)
        programme = _text(row, "programme_id", c)
        level = _text(row, "level", c)
        semester = _semester(row, "semester", c)
        credits = _integer(row, "credits", c, minimum=0)
        if identifier is None or code is None or department is None or programme is None:
            continue
        if level is None or semester is None or credits is None:
            continue
        built.append(
            (
                row,
                Course(
                    id=identifier,
                    code=code,
                    department=department,
                    programme=programme,
                    level=level,
                    semester=semester,
                    credits=credits,
                ),
            )
        )
    return _unique(built, lambda c_: c_.id, "course_id", c)


def _sessions(rows: list[_Row], c: _Collector) -> list[Session]:
    built: list[tuple[_Row, Session]] = []
    for row in rows:
        identifier = _text(row, "session_id", c)
        course = _text(row, "course_id", c)
        group = _text(row, "group_id", c)
        teacher = _text(row, "teacher_id", c)
        kind = _enum(row, "session_type", c, SessionType, SessionType)
        room_type = _enum(row, "required_room_type", c, RoomType, RoomType)
        locked = _boolean(row, "is_locked", c)
        occurrences = _integer(row, "occurrences_per_week", c, minimum=1)
        duration = _integer(row, "duration_periods", c, minimum=1)
        if duration is not None and duration > 2:
            # docs/domain-model.md and C-7: a session spans one or two periods.
            # H8 keeps a two-period session inside one day and the pre-analysis
            # counts two-period windows; a three-period session has no window
            # supply computed for it anywhere.
            c.reject(
                row.line,
                "a session spans 1 or 2 periods",
                field="duration_periods",
                value=row.values["duration_periods"].strip(),
            )
            duration = None
        if identifier is None or course is None or group is None or teacher is None:
            continue
        if kind is None or room_type is None or locked is None:
            continue
        if occurrences is None or duration is None:
            continue
        built.append(
            (
                row,
                Session(
                    id=identifier,
                    course=course,
                    group=group,
                    teacher=teacher,
                    type=kind,
                    duration_periods=duration,
                    occurrences_per_week=occurrences,
                    required_room_type=room_type,
                    locked=locked,
                ),
            )
        )
    return _unique(built, lambda s: s.id, "session_id", c)


def _rooms(rows: list[_Row], c: _Collector) -> list[Room]:
    built: list[tuple[_Row, Room]] = []
    for row in rows:
        identifier = _text(row, "room_id", c)
        building = _text(row, "building", c)
        code = _text(row, "code", c)
        capacity = _integer(row, "capacity", c, minimum=1)
        room_type = _enum(row, "room_type", c, RoomType, RoomType)
        equipment: list[str] = []
        for name, column in (("projector", "has_projector"), ("computers", "has_computers")):
            if column in row.values and row.values[column].strip():
                present = _boolean(row, column, c)
                if present is None:
                    capacity = None  # a bad flag rejects the line, like any other field
                elif present:
                    equipment.append(name)
        if identifier is None or building is None or code is None:
            continue
        if capacity is None or room_type is None:
            continue
        built.append(
            (
                row,
                Room(
                    id=identifier,
                    building=building,
                    code=code,
                    capacity=capacity,
                    type=room_type,
                    equipment=tuple(equipment),
                ),
            )
        )
    return _unique(built, lambda r: r.id, "room_id", c)


def _slots(rows: list[_Row], c: _Collector) -> list[Slot]:
    built: list[tuple[_Row, Slot]] = []
    for row in rows:
        index = _integer(row, "slot_id", c, minimum=0)
        day = _integer(row, "day_index", c, minimum=0)
        period = _integer(row, "period_index", c, minimum=0)
        start = _clock(row, "start_time", c)
        end = _clock(row, "end_time", c)
        is_open = _boolean(row, "is_open", c)
        if start is not None and end is not None and end <= start:
            c.reject(
                row.line,
                "the slot ends before it starts",
                field="end_time",
                value=row.values["end_time"].strip(),
            )
            end = None
        if index is None or day is None or period is None:
            continue
        if start is None or end is None or is_open is None:
            continue
        built.append(
            (
                row,
                Slot(
                    index=index,
                    day_index=day,
                    period_index=period,
                    start_hour=start,
                    end_hour=end,
                    is_open=is_open,
                ),
            )
        )
    return _unique(built, lambda s: s.index, "slot_id", c)


def _availability(rows: list[_Row], c: _Collector) -> list[Availability]:
    built: list[Availability] = []
    for row in rows:
        teacher = _text(row, "teacher_id", c)
        slot = _integer(row, "slot_id", c, minimum=0)
        available = _boolean(row, "is_available", c)
        semester = _semester(row, "semester", c)
        source = _enum(row, "source", c, DeclarationSource, DeclarationSource)
        if teacher is None or slot is None or available is None:
            continue
        if semester is None or source is None:
            continue
        built.append(
            Availability(
                teacher=teacher,
                slot=slot,
                state=(AvailabilityState.AVAILABLE if available else AvailabilityState.UNAVAILABLE),
                semester=semester,
                source=source,
            )
        )
    return built


def _holidays(rows: list[_Row], c: _Collector) -> list[Holiday]:
    built: list[Holiday] = []
    for row in rows:
        when = _calendar_date(row, "holiday_date", c)
        label = _text(row, "label", c)
        lunar = _boolean(row, "is_islamic", c)
        approximate = _boolean(row, "is_approximate", c)
        blocking = _boolean(row, "blocks_scheduling", c)
        if when is None or label is None:
            continue
        if lunar is None or approximate is None or blocking is None:
            continue
        built.append(
            Holiday(
                date=when,
                label=label,
                lunar=lunar,
                approximate=approximate,
                blocking=blocking,
            )
        )
    return built


def _calendar_config(rows: list[_Row], c: _Collector) -> dict[str, str]:
    config: dict[str, str] = {}
    first_line: dict[str, int] = {}
    for row in rows:
        key = _text(row, "key", c)
        if key is None:
            continue
        if key in first_line:
            c.reject(
                row.line,
                f"duplicate identifier; already declared on line {first_line[key]}",
                field="key",
                value=key,
            )
            continue
        first_line[key] = row.line
        config[key] = row.values["value"].strip()
    return config


# ── References ─────────────────────────────────────────────────────────


def _check_references(
    *,
    programmes: list[Programme],
    promotions: list[Promotion],
    groups: list[Group],
    teachers: list[Teacher],
    courses: list[Course],
    sessions: list[Session],
    rooms: list[Room],
    slots: list[Slot],
    availability: list[Availability],
    rows: Mapping[str, list[_Row]],
) -> list[RejectedLine]:
    """Every reference must name something the same dataset declares.

    Reported against the line that *makes* the reference, because that is the
    line a person has to edit. A dataset is verified whole, so a session may
    refer to a course declared after it — order in the files carries no meaning.
    """
    rejected: list[RejectedLine] = []

    def check[T](
        file: str,
        entities: list[T],
        field: str,
        value_of: Callable[[T], str | int | None],
        known: set[str] | set[int],
        what: str,
    ) -> None:
        # `entities` and `rows[file]` are parallel only for files whose rows all
        # survived, which is exactly when this runs: reference checking is
        # skipped entirely while any line is rejected (see `validate_dataset`).
        # `strict=True` therefore doubles as an assertion of that invariant.
        for row, entity in zip(rows[file], entities, strict=True):
            value = value_of(entity)
            if value is not None and value not in known:
                rejected.append(
                    RejectedLine(
                        file=file,
                        line=row.line,
                        reason=f"no {what} with this identifier is declared in this dataset",
                        field=field,
                        value=str(value),
                    )
                )

    programme_ids = {p.id for p in programmes}
    promotion_ids = {p.id for p in promotions}
    group_ids = {g.id for g in groups}
    teacher_ids = {t.id for t in teachers}
    course_ids = {c.id for c in courses}
    room_types = {r.type for r in rooms}
    slot_indices = {s.index for s in slots}

    check(PROMOTIONS, promotions, "programme_id", lambda e: e.programme, programme_ids, "programme")
    check(GROUPS, groups, "promotion_id", lambda e: e.promotion, promotion_ids, "promotion")
    check(GROUPS, groups, "parent_group_id", lambda e: e.parent_group, group_ids, "group")
    check(COURSES, courses, "programme_id", lambda e: e.programme, programme_ids, "programme")
    check(SESSIONS, sessions, "course_id", lambda e: e.course, course_ids, "course")
    check(SESSIONS, sessions, "group_id", lambda e: e.group, group_ids, "group")
    check(SESSIONS, sessions, "teacher_id", lambda e: e.teacher, teacher_ids, "teacher")
    check(AVAILABILITY, availability, "teacher_id", lambda e: e.teacher, teacher_ids, "teacher")
    check(AVAILABILITY, availability, "slot_id", lambda e: e.slot, slot_indices, "slot")

    # A session's required room type must be a type some room actually has.
    # This is a reference into `rooms.csv` even though it is spelled as an enum:
    # H4 restricts a session to rooms of its type, and a type no room carries
    # leaves that session with an empty domain and no timetable at all.
    for row, session in zip(rows[SESSIONS], sessions, strict=True):
        if session.required_room_type not in room_types:
            rejected.append(
                RejectedLine(
                    file=SESSIONS,
                    line=row.line,
                    reason="no room of this type is declared in this dataset",
                    field="required_room_type",
                    value=str(session.required_room_type),
                )
            )

    rejected.extend(_check_hierarchy_is_acyclic(groups, rows[GROUPS]))
    return rejected


def _check_hierarchy_is_acyclic(groups: list[Group], rows: list[_Row]) -> list[RejectedLine]:
    """No group may be its own ancestor.

    ⚠️ **Checked here rather than left to FR-12, and the reason is a hang.**
    `solver/constraints/overlap.py::_ancestor_chain` walks parents with
    `while current is not None`, and `tasks/executor.py` does not stop a run
    when a pre-analysis check fails — so a cycle reaching stage 2 spins the run
    thread forever instead of failing it. The level rule (`PROMO → TD → TP`)
    stays with `preanalysis.verifications.GroupHierarchy`, which reports it.
    """
    parent_of = {g.id: g.parent_group for g in groups}
    rejected: list[RejectedLine] = []
    for row, group in zip(rows, groups, strict=True):
        seen: set[str] = set()
        current: str | None = group.id
        while current is not None and current in parent_of:
            if current in seen:
                rejected.append(
                    RejectedLine(
                        file=GROUPS,
                        line=row.line,
                        reason=(
                            "this group is its own ancestor; the promotion → TD → TP "
                            "hierarchy must not contain a cycle"
                        ),
                        field="parent_group_id",
                        value=str(group.parent_group),
                    )
                )
                break
            seen.add(current)
            current = parent_of[current]
    return rejected


def _order(rejected: Iterable[RejectedLine]) -> tuple[RejectedLine, ...]:
    """File order, then line order — the order somebody would work through them."""
    position = {name: i for i, name in enumerate(DEPARTMENT_FILES)}
    return tuple(
        sorted(
            rejected,
            key=lambda r: (position.get(r.file, len(position)), r.line or 0, r.field or ""),
        )
    )


def validate_dataset(
    files: Mapping[str, str],
    constraints: tuple[ConstraintDefinition, ...],
) -> ValidationResult:
    """Verify a supplied department dataset and build its Instance, or report.

    `files` maps a name in `DEPARTMENT_FILES` to that file's text. A name that
    is not a department file is rejected rather than ignored — silently
    discarding `constraint_catalogue.csv` would leave the person who sent it
    believing the catalogue had been replaced.

    ⚠️ **`constraints` is supplied by the CALLER, never by the dataset**, and
    that parameter is where the catalogue's exclusion is enforced rather than
    merely documented: there is no code path by which a supplied file can reach
    `Instance.constraints`. The caller passes the application's own catalogue,
    read from `data/instance/constraint_catalogue.csv` by the loader.

    ⚠️ **References are checked only once every line parses.** A dataset with a
    malformed row has an incomplete set of identifiers, so reference checking
    would report absences caused by the fault already reported — one defect
    producing two reports, the second of which disappears when the first is
    fixed.
    """
    rejected: list[RejectedLine] = []

    unexpected = sorted(set(files) - set(DEPARTMENT_FILES))
    for name in unexpected:
        rejected.append(
            RejectedLine(
                file=name,
                line=None,
                reason=(
                    "not part of a department dataset; the accepted files are: "
                    + ", ".join(DEPARTMENT_FILES)
                ),
            )
        )

    missing = [name for name in DEPARTMENT_FILES if name not in files]
    for name in missing:
        rejected.append(RejectedLine(file=name, line=None, reason="required file is missing"))

    if rejected:
        return ValidationResult(instance=None, rejected=_order(rejected))

    collectors = {name: _Collector(name) for name in DEPARTMENT_FILES}
    rows = {name: _read_rows(files[name], name, collectors[name]) for name in DEPARTMENT_FILES}

    programmes = _programmes(rows[PROGRAMMES], collectors[PROGRAMMES])
    promotions = _promotions(rows[PROMOTIONS], collectors[PROMOTIONS])
    groups = _groups(rows[GROUPS], collectors[GROUPS])
    teachers = _teachers(rows[TEACHERS], collectors[TEACHERS])
    courses = _courses(rows[COURSES], collectors[COURSES])
    sessions = _sessions(rows[SESSIONS], collectors[SESSIONS])
    rooms = _rooms(rows[ROOMS], collectors[ROOMS])
    slots = _slots(rows[SLOTS], collectors[SLOTS])
    availability = _availability(rows[AVAILABILITY], collectors[AVAILABILITY])
    holidays = _holidays(rows[HOLIDAYS], collectors[HOLIDAYS])
    config = _calendar_config(rows[CALENDAR_CONFIG], collectors[CALENDAR_CONFIG])

    for collector in collectors.values():
        rejected.extend(collector.rejected)

    if rejected:
        return ValidationResult(instance=None, rejected=_order(rejected))

    rejected.extend(
        _check_references(
            programmes=programmes,
            promotions=promotions,
            groups=groups,
            teachers=teachers,
            courses=courses,
            sessions=sessions,
            rooms=rooms,
            slots=slots,
            availability=availability,
            rows=rows,
        )
    )

    # A dataset that declares no session, no room or no slot cannot produce a
    # timetable at all. Reported as a fault of the file rather than of a line,
    # since there is no line to point at.
    for name, present in (
        (SESSIONS, sessions),
        (ROOMS, rooms),
        (SLOTS, slots),
        (GROUPS, groups),
        (TEACHERS, teachers),
    ):
        if not present:
            rejected.append(
                RejectedLine(file=name, line=None, reason="the file declares no entity")
            )

    if rejected:
        return ValidationResult(instance=None, rejected=_order(rejected), references_checked=True)

    return ValidationResult(
        instance=Instance(
            programmes=tuple(programmes),
            promotions=tuple(promotions),
            groups=tuple(groups),
            teachers=tuple(teachers),
            courses=tuple(courses),
            sessions=tuple(sessions),
            rooms=tuple(rooms),
            slots=tuple(slots),
            availability=tuple(availability),
            holidays=tuple(holidays),
            calendar_config=config,
            constraints=constraints,
        ),
        rejected=(),
        references_checked=True,
    )


def iter_rejections(result: ValidationResult) -> Iterator[str]:
    """Human-readable lines, for a log or a message. The API sends the objects."""
    for rejection in result.rejected:
        yield rejection.describe()
