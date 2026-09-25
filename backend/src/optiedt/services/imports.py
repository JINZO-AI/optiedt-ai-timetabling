"""Staged imports of reference and term data from CSV or XLSX files.

1. Upload: the file is parsed (CSV in UTF-8 or Windows-1252 with any common delimiter, or
   the first sheet of an XLSX workbook) and its rows are stored with a suggested mapping from
   columns to fields.
2. Map: the mapping is confirmed or corrected and every row is validated: what it would
   create or update, and every problem per field.
3. Commit: rows are validated again and applied in one transaction through the same services
   as manual edits (permissions, validation and audit included). Any error applies nothing.
"""

from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from optiedt.errors import AppError, Conflict, FieldError, InvalidInput, NotFound, PermissionDenied
from optiedt.models import (
    Activity,
    ActivityType,
    Building,
    Campus,
    Course,
    Department,
    ImportBatch,
    Instructor,
    Programme,
    Room,
    RoomFeature,
    RoomType,
    StudentGroup,
)
from optiedt.security.permissions import Permission, Principal
from optiedt.services import activities as activity_service
from optiedt.services import audit, reference, resources
from optiedt.services import groups as group_service
from optiedt.services.terms import get_term

MAX_ROWS = 10_000
MAX_COLUMNS = 60
LIST_SEPARATORS = (";", "|", ",")
DELIMITERS = (",", ";", "\t", "|")
TRUE = {"1", "true", "yes", "y", "x", "oui", "o", "vrai", "نعم"}
FALSE = {"0", "false", "no", "n", "non", "faux", "لا", ""}


# ── specifications ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Column:
    name: str
    label: str
    kind: str
    """``text``, ``int``, ``float``, ``bool`` or ``list``."""
    required: bool = False
    synonyms: tuple[str, ...] = ()
    example: str = ""


@dataclass(frozen=True, slots=True)
class Spec:
    code: str
    label: str
    term_scoped: bool
    columns: tuple[Column, ...]

    def column(self, name: str) -> Column:
        return next(c for c in self.columns if c.name == name)


SPECS: dict[str, Spec] = {
    spec.code: spec
    for spec in (
        Spec(
            "rooms",
            "Rooms",
            False,
            (
                Column("code", "Code", "text", True, ("room", "salle", "room code"), "B-104"),
                Column(
                    "name", "Name", "text", False, ("nom", "room name", "libelle"), "Seminar room"
                ),
                Column(
                    "building", "Building", "text", True, ("batiment", "bloc", "building code"), "B"
                ),
                Column(
                    "room_type",
                    "Room type",
                    "text",
                    True,
                    ("type", "type de salle", "roomtype"),
                    "CLASSROOM",
                ),
                Column(
                    "capacity",
                    "Capacity",
                    "int",
                    True,
                    ("capacite", "places", "seats", "size"),
                    "36",
                ),
                Column(
                    "features",
                    "Features",
                    "list",
                    False,
                    ("equipements", "equipment", "caracteristiques"),
                    "PROJECTOR;WHITEBOARD",
                ),
                Column("department", "Department", "text", False, ("departement", "dept"), "CS"),
                Column("is_active", "Active", "bool", False, ("actif", "active"), "yes"),
            ),
        ),
        Spec(
            "instructors",
            "Instructors",
            False,
            (
                Column(
                    "code",
                    "Staff code",
                    "text",
                    True,
                    ("code", "matricule", "staff code", "id"),
                    "T105",
                ),
                Column(
                    "first_name",
                    "First name",
                    "text",
                    True,
                    ("prenom", "firstname", "given name"),
                    "Amira",
                ),
                Column(
                    "last_name",
                    "Last name",
                    "text",
                    True,
                    ("nom", "lastname", "surname", "family name"),
                    "Haddad",
                ),
                Column(
                    "email",
                    "Email",
                    "text",
                    False,
                    ("e-mail", "mail", "courriel"),
                    "a.haddad@example.edu",
                ),
                Column("title", "Title", "text", False, ("titre", "grade"), "Dr"),
                Column("department", "Department", "text", True, ("departement", "dept"), "CS"),
                Column(
                    "max_weekly_periods",
                    "Maximum periods per week",
                    "int",
                    False,
                    ("max periods", "charge max", "max weekly periods"),
                    "12",
                ),
                Column("is_active", "Active", "bool", False, ("actif", "active"), "yes"),
            ),
        ),
        Spec(
            "courses",
            "Courses",
            False,
            (
                Column(
                    "code",
                    "Code",
                    "text",
                    True,
                    ("course", "cours", "matiere", "course code"),
                    "CS301",
                ),
                Column(
                    "title",
                    "Title",
                    "text",
                    True,
                    ("intitule", "name", "nom", "libelle"),
                    "Operating systems",
                ),
                Column("department", "Department", "text", True, ("departement", "dept"), "CS"),
                Column(
                    "credits", "Credits", "float", False, ("credits", "ects", "coefficient"), "6"
                ),
            ),
        ),
        Spec(
            "groups",
            "Student groups",
            True,
            (
                Column("code", "Code", "text", True, ("group", "groupe", "group code"), "L3-CS-G1"),
                Column("name", "Name", "text", True, ("nom", "libelle"), "L3 CS group 1"),
                Column(
                    "size",
                    "Size",
                    "int",
                    True,
                    ("effectif", "students", "etudiants", "headcount"),
                    "30",
                ),
                Column(
                    "parent",
                    "Parent group",
                    "text",
                    False,
                    ("parent", "groupe parent", "cohort"),
                    "L3-CS",
                ),
                Column(
                    "partition_key",
                    "Partition",
                    "text",
                    False,
                    ("partition", "division", "split"),
                    "tutorial",
                ),
                Column(
                    "programme",
                    "Programme",
                    "text",
                    False,
                    ("programme", "filiere", "program"),
                    "BSC-CS",
                ),
            ),
        ),
        Spec(
            "activities",
            "Activities",
            True,
            (
                Column(
                    "course", "Course", "text", True, ("cours", "matiere", "course code"), "CS301"
                ),
                Column(
                    "type",
                    "Activity type",
                    "text",
                    True,
                    ("type", "nature", "activity type"),
                    "TUT",
                ),
                Column(
                    "groups", "Groups", "list", True, ("groupes", "group", "groupe"), "L3-CS-G1"
                ),
                Column(
                    "instructors",
                    "Instructors",
                    "list",
                    False,
                    ("enseignants", "instructor", "enseignant", "teachers"),
                    "T105",
                ),
                Column("label", "Label", "text", False, ("libelle", "label"), ""),
                Column(
                    "duration",
                    "Periods per session",
                    "int",
                    False,
                    ("duree", "duration", "periods"),
                    "1",
                ),
                Column(
                    "sessions_per_week",
                    "Sessions per week",
                    "int",
                    False,
                    ("seances", "sessions", "frequency", "per week"),
                    "1",
                ),
                Column("room_type", "Room type", "text", False, ("type de salle", "room type"), ""),
                Column(
                    "features", "Required features", "list", False, ("equipements", "features"), ""
                ),
                Column(
                    "min_capacity",
                    "Seats needed",
                    "int",
                    False,
                    ("places", "capacity", "seats"),
                    "",
                ),
                Column("online", "Online", "bool", False, ("en ligne", "distance", "online"), "no"),
                Column(
                    "different_days",
                    "Sessions on different days",
                    "bool",
                    False,
                    ("jours differents", "different days"),
                    "yes",
                ),
            ),
        ),
    )
}


# ── parsing files ──────────────────────────────────────────────────────


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_file(filename: str, content: bytes) -> tuple[list[str], list[list[str]]]:
    """Header row and data rows of a CSV or XLSX file, blank rows and columns dropped."""
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        table = _read_xlsx(content)
    elif name.endswith((".csv", ".txt", ".tsv")):
        table = _read_csv(content)
    else:
        raise InvalidInput("Upload a .csv or .xlsx file.", [FieldError("file", filename)])
    table = [row for row in table if any(cell for cell in row)]
    if not table:
        raise InvalidInput("The file is empty.", [FieldError("file", filename)])
    width = max(len(row) for row in table)
    if width > MAX_COLUMNS:
        raise InvalidInput(f"The file has more than {MAX_COLUMNS} columns.")
    if len(table) - 1 > MAX_ROWS:
        raise InvalidInput(f"The file has more than {MAX_ROWS} rows; split it.")
    rows = [row + [""] * (width - len(row)) for row in table]
    return rows[0], rows[1:]


def _read_csv(content: bytes) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise InvalidInput("The file is neither UTF-8 nor Windows-1252 text.")
    # The header line decides the delimiter: headers seldom contain one, while data rows may
    # be short or hold commas inside quoted text.
    header = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = max(DELIMITERS, key=header.count)
    if not header.count(delimiter):
        delimiter = ","
    return [
        [cell.strip() for cell in row]
        for row in csv.reader(io.StringIO(text), delimiter=delimiter)
    ]


def _read_xlsx(content: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as error:  # openpyxl raises many kinds for damaged files
        raise InvalidInput("The workbook could not be read. Save it again as .xlsx.") from error
    try:
        sheet = workbook.worksheets[0]
        return [[_cell(value) for value in row] for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _normal(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if ch.isalnum())


def suggest_mapping(spec: Spec, headers: list[str]) -> dict[str, int]:
    """Column index for every field whose name, label or synonym matches a header."""
    normalized = [_normal(h) for h in headers]
    mapping: dict[str, int] = {}
    for column in spec.columns:
        names = {
            _normal(column.name),
            _normal(column.label),
            *(_normal(s) for s in column.synonyms),
        }
        for index, header in enumerate(normalized):
            if header in names and index not in mapping.values():
                mapping[column.name] = index
                break
    return mapping


# ── reading rows ───────────────────────────────────────────────────────


@dataclass
class Row:
    number: int
    """Line in the file, the header being line 1."""
    key: str | None
    action: str = "create"
    """``create``, ``update``, ``unchanged`` or ``error``."""
    values: dict[str, Any] = field(default_factory=dict)
    existing: Any = None
    errors: list[FieldError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {
            "row": self.number,
            "key": self.key,
            "action": self.action,
            "errors": [{"field": e.field, "message": e.message} for e in self.errors],
            "warnings": self.warnings,
        }


def _parse(column: Column, raw: str, row: Row) -> Any:
    if raw == "":
        if column.required:
            row.errors.append(FieldError(column.name, f"{column.label} is required."))
        return None
    if column.kind == "int":
        try:
            number = float(raw.replace(",", "."))
        except ValueError:
            row.errors.append(FieldError(column.name, f"'{raw}' is not a whole number."))
            return None
        if not number.is_integer() or number < 0:
            row.errors.append(FieldError(column.name, f"'{raw}' is not a whole number."))
            return None
        return int(number)
    if column.kind == "float":
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            row.errors.append(FieldError(column.name, f"'{raw}' is not a number."))
            return None
    if column.kind == "bool":
        lowered = raw.lower()
        if lowered in TRUE:
            return True
        if lowered in FALSE:
            return False
        row.errors.append(FieldError(column.name, f"'{raw}' is not yes or no."))
        return None
    if column.kind == "list":
        separator = next((s for s in LIST_SEPARATORS if s in raw), ";")
        return [part.strip() for part in raw.split(separator) if part.strip()]
    return raw


class Lookup:
    """Codes of existing records, matched without regard to case."""

    def __init__(self, db: Session, model: Any, *where: Any) -> None:
        statement = select(model.code, model.id).where(*where)
        self.ids: dict[str, uuid.UUID] = {
            code.upper(): identifier for code, identifier in db.execute(statement).all()
        }

    def resolve(self, code: str | None, row: Row, column: str, label: str) -> uuid.UUID | None:
        if code is None:
            return None
        found = self.ids.get(code.upper())
        if found is None:
            row.errors.append(FieldError(column, f"Unknown {label} '{code}'."))
        return found

    def resolve_all(
        self, codes: list[str] | None, row: Row, column: str, label: str
    ) -> list[uuid.UUID]:
        return [
            identifier
            for code in codes or []
            if (identifier := self.resolve(code, row, column, label)) is not None
        ]


def _rows(spec: Spec, batch: ImportBatch) -> list[tuple[Row, dict[str, Any]]]:
    mapping: dict[str, int] = {k: int(v) for k, v in batch.mapping.get("columns", {}).items()}
    result = []
    for position, cells in enumerate(batch.rows, start=2):
        row = Row(number=position, key=None)
        parsed = {
            column.name: _parse(
                column, cells[mapping[column.name]] if column.name in mapping else "", row
            )
            for column in spec.columns
        }
        result.append((row, parsed))
    return result


def _differs(record: Any, values: dict[str, Any]) -> bool:
    return any(
        getattr(record, name) != value
        for name, value in values.items()
        if hasattr(record, name) and name not in ("feature_ids",)
    )


# ── validation per entity type ─────────────────────────────────────────


def _rooms(db: Session, rows: list[tuple[Row, dict[str, Any]]], batch: ImportBatch) -> None:
    buildings: dict[str, list[tuple[uuid.UUID, str]]] = {}
    for building, campus in db.execute(
        select(Building, Campus.code).join(Campus, Campus.id == Building.campus_id)
    ).all():
        buildings.setdefault(building.code.upper(), []).append((building.id, campus))
    types = Lookup(db, RoomType)
    features = Lookup(db, RoomFeature)
    departments = Lookup(db, Department)
    existing = {(r.building_id, r.code.upper()): r for r in db.scalars(select(Room))}
    for row, v in rows:
        choices = buildings.get((v["building"] or "").upper(), [])
        building_id = None
        if v["building"] is not None and not choices:
            row.errors.append(FieldError("building", f"Unknown building '{v['building']}'."))
        elif len(choices) > 1:
            row.errors.append(
                FieldError("building", f"Building '{v['building']}' exists on several campuses.")
            )
        elif choices:
            building_id = choices[0][0]
        values = {
            "code": v["code"],
            "name": v["name"],
            "building_id": building_id,
            "room_type_id": types.resolve(v["room_type"], row, "room_type", "room type"),
            "capacity": v["capacity"],
            "department_id": departments.resolve(v["department"], row, "department", "department"),
            "feature_ids": features.resolve_all(v["features"], row, "features", "feature"),
        }
        if v["is_active"] is not None:
            values["is_active"] = v["is_active"]
        row.key = v["code"]
        row.values = values
        if building_id is not None:
            row.existing = existing.get((building_id, (v["code"] or "").upper()))


def _instructors(db: Session, rows: list[tuple[Row, dict[str, Any]]], batch: ImportBatch) -> None:
    departments = Lookup(db, Department)
    existing = {i.code.upper(): i for i in db.scalars(select(Instructor))}
    for row, v in rows:
        values = {
            name: v[name]
            for name in ("code", "first_name", "last_name", "email", "title", "max_weekly_periods")
        }
        values["department_id"] = departments.resolve(
            v["department"], row, "department", "department"
        )
        if v["is_active"] is not None:
            values["is_active"] = v["is_active"]
        row.key = v["code"]
        row.values = values
        row.existing = existing.get((v["code"] or "").upper())


def _courses(db: Session, rows: list[tuple[Row, dict[str, Any]]], batch: ImportBatch) -> None:
    departments = Lookup(db, Department)
    existing = {c.code.upper(): c for c in db.scalars(select(Course))}
    for row, v in rows:
        row.key = v["code"]
        row.values = {
            "code": v["code"],
            "title": v["title"],
            "credits": v["credits"],
            "department_id": departments.resolve(v["department"], row, "department", "department"),
        }
        row.existing = existing.get((v["code"] or "").upper())


def _groups(db: Session, rows: list[tuple[Row, dict[str, Any]]], batch: ImportBatch) -> None:
    term_id = batch.term_id
    programmes = Lookup(db, Programme)
    existing = {
        g.code.upper(): g
        for g in db.scalars(select(StudentGroup).where(StudentGroup.term_id == term_id))
    }
    in_file = {(v["code"] or "").upper() for _, v in rows}
    for row, v in rows:
        parent = (v["parent"] or "").upper() or None
        if parent is not None and parent not in existing and parent not in in_file:
            row.errors.append(FieldError("parent", f"Unknown parent group '{v['parent']}'."))
        row.key = v["code"]
        row.values = {
            "code": v["code"],
            "name": v["name"],
            "size": v["size"],
            "partition_key": v["partition_key"] or "default",
            "programme_id": programmes.resolve(v["programme"], row, "programme", "programme"),
            "parent_code": parent,
        }
        row.existing = existing.get((v["code"] or "").upper())


def _activities(db: Session, rows: list[tuple[Row, dict[str, Any]]], batch: ImportBatch) -> None:
    term_id = batch.term_id
    courses = Lookup(db, Course)
    types = Lookup(db, ActivityType)
    groups = Lookup(db, StudentGroup, StudentGroup.term_id == term_id)
    instructors = Lookup(db, Instructor)
    room_types = Lookup(db, RoomType)
    features = Lookup(db, RoomFeature)
    known = {
        (a.course_id, a.activity_type_id, a.label or "")
        for a in db.scalars(select(Activity).where(Activity.term_id == term_id))
    }
    for row, v in rows:
        values: dict[str, Any] = {
            "course_id": courses.resolve(v["course"], row, "course", "course"),
            "activity_type_id": types.resolve(v["type"], row, "type", "activity type"),
            "group_ids": groups.resolve_all(v["groups"], row, "groups", "group"),
            "instructor_ids": instructors.resolve_all(
                v["instructors"], row, "instructors", "instructor"
            ),
            "label": v["label"],
            "duration": v["duration"] or 1,
            "sessions_per_week": v["sessions_per_week"] or 1,
            "room_type_id": room_types.resolve(v["room_type"], row, "room_type", "room type"),
            "feature_ids": features.resolve_all(v["features"], row, "features", "feature"),
            "min_capacity": v["min_capacity"],
            "delivery_mode": "online" if v["online"] else "in_person",
            "different_days": True if v["different_days"] is None else v["different_days"],
        }
        row.key = f"{v['course']} {v['type']}" + (f" {v['label']}" if v["label"] else "")
        row.values = values
        if (values["course_id"], values["activity_type_id"], v["label"] or "") in known:
            row.warnings.append(
                "The term already has an activity of this course, type and label; "
                "importing adds another one."
            )


VALIDATORS: dict[str, Callable[[Session, list[tuple[Row, dict[str, Any]]], ImportBatch], None]] = {
    "rooms": _rooms,
    "instructors": _instructors,
    "courses": _courses,
    "groups": _groups,
    "activities": _activities,
}


def validate_rows(db: Session, batch: ImportBatch) -> list[Row]:
    spec = SPECS[batch.entity_type]
    parsed = _rows(spec, batch)
    VALIDATORS[batch.entity_type](db, parsed, batch)
    rows = [row for row, _ in parsed]
    seen: dict[str, int] = {}
    for row in rows:
        if batch.entity_type != "activities" and row.key:
            first = seen.setdefault(row.key.upper(), row.number)
            if first != row.number:
                row.errors.append(FieldError("code", f"Also on line {first} of the file."))
        if row.errors:
            row.action = "error"
        elif batch.entity_type == "activities" or row.existing is None:
            row.action = "create"
        elif not batch.mapping.get("update_existing", True):
            row.action = "error"
            row.errors.append(FieldError("code", "Already exists; updating is switched off."))
        else:
            comparable = {k: v for k, v in row.values.items() if k not in ("parent_code",)}
            row.action = (
                "update"
                if _differs(row.existing, comparable) or "feature_ids" in comparable
                else "unchanged"
            )
    return rows


def _report(rows: list[Row]) -> dict[str, Any]:
    counts = dict.fromkeys(("create", "update", "unchanged", "error"), 0)
    for row in rows:
        counts[row.action] += 1
    return {"counts": counts, "rows": [row.as_json() for row in rows if row.action != "unchanged"]}


# ── batches ────────────────────────────────────────────────────────────


def _require(principal: Principal) -> None:
    if not principal.can(Permission.IMPORTS_RUN):
        raise PermissionDenied()


def get_batch(db: Session, principal: Principal, batch_id: uuid.UUID) -> ImportBatch:
    _require(principal)
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise NotFound("Import")
    if (
        not principal.scope(Permission.IMPORTS_RUN).everywhere
        and batch.created_by_id != principal.user_id
    ):
        raise NotFound("Import")
    return batch


def upload(
    db: Session,
    principal: Principal,
    *,
    entity_type: str,
    term_id: uuid.UUID | None,
    filename: str,
    content: bytes,
) -> ImportBatch:
    _require(principal)
    spec = SPECS.get(entity_type)
    if spec is None:
        raise InvalidInput("Unknown kind of import.", [FieldError("entity_type", entity_type)])
    if spec.term_scoped:
        if term_id is None:
            raise InvalidInput(
                "Choose the term to import into.", [FieldError("term_id", "required")]
            )
        get_term(db, term_id)
    else:
        term_id = None
    headers, rows = parse_file(filename, content)
    batch = ImportBatch(
        entity_type=entity_type,
        term_id=term_id,
        filename=filename[:255],
        file_sha256=hashlib.sha256(content).hexdigest(),
        headers=headers,
        rows=rows,
        mapping={"columns": suggest_mapping(spec, headers), "update_existing": True},
        created_by_id=principal.user_id,
    )
    db.add(batch)
    db.flush()
    batch.report = _report(validate_rows(db, batch))
    db.flush()
    return batch


def set_mapping(
    db: Session,
    principal: Principal,
    batch_id: uuid.UUID,
    *,
    columns: dict[str, int],
    update_existing: bool,
) -> ImportBatch:
    batch = get_batch(db, principal, batch_id)
    if batch.status != "uploaded":
        raise Conflict("This import is already closed.", code="import_closed")
    spec = SPECS[batch.entity_type]
    errors = [
        FieldError(f"columns.{name}", "Unknown field.")
        for name in columns
        if name not in {c.name for c in spec.columns}
    ]
    errors += [
        FieldError(f"columns.{name}", "No such column.")
        for name, index in columns.items()
        if not 0 <= index < len(batch.headers)
    ]
    if errors:
        raise InvalidInput("The mapping is invalid.", errors)
    batch.mapping = {"columns": dict(columns), "update_existing": update_existing}
    batch.report = _report(validate_rows(db, batch))
    db.flush()
    return batch


def discard(db: Session, principal: Principal, batch_id: uuid.UUID) -> None:
    batch = get_batch(db, principal, batch_id)
    if batch.status == "uploaded":
        batch.status = "discarded"
        batch.rows = []
        db.flush()


def commit(db: Session, principal: Principal, batch_id: uuid.UUID) -> ImportBatch:
    batch = get_batch(db, principal, batch_id)
    if batch.status != "uploaded":
        raise Conflict("This import is already closed.", code="import_closed")
    rows = validate_rows(db, batch)
    report = _report(rows)
    if report["counts"]["error"]:
        batch.report = report
        raise Conflict(
            f"{report['counts']['error']} row(s) have problems; nothing was imported.",
            code="import_has_errors",
        )
    created_groups: dict[str, uuid.UUID] = {}
    for row in _ordered(batch.entity_type, rows):
        if row.action == "unchanged":
            continue
        try:
            _apply(db, principal, batch, row, created_groups)
        except AppError as error:
            raise InvalidInput(f"Line {row.number}: {error.message}", error.errors) from error
    batch.status = "committed"
    batch.committed_at = datetime.now(UTC)
    batch.report = report
    batch.rows = []
    db.flush()
    audit.record(
        db,
        principal,
        action="import.commit",
        entity_type="import_batch",
        entity_id=batch.id,
        summary=(
            f"Imported {batch.entity_type} from {batch.filename}: "
            f"{report['counts']['create']} created, {report['counts']['update']} updated"
        ),
        term_id=batch.term_id,
    )
    return batch


def _ordered(entity_type: str, rows: list[Row]) -> list[Row]:
    """Groups are created parents first."""
    if entity_type != "groups":
        return rows
    by_code = {(row.key or "").upper(): row for row in rows}
    ordered: list[Row] = []
    placed: set[str] = set()

    def visit(row: Row, path: set[str]) -> None:
        code = (row.key or "").upper()
        if code in placed:
            return
        if code in path:
            raise InvalidInput(f"Line {row.number}: the group is its own ancestor.")
        parent = row.values.get("parent_code")
        if parent in by_code:
            visit(by_code[parent], path | {code})
        placed.add(code)
        ordered.append(row)

    for row in rows:
        visit(row, set())
    return ordered


def _apply(
    db: Session,
    principal: Principal,
    batch: ImportBatch,
    row: Row,
    created_groups: dict[str, uuid.UUID],
) -> None:
    values = dict(row.values)
    kind = batch.entity_type
    if kind in ("rooms", "instructors", "courses"):
        resource = {
            "rooms": reference.ROOMS,
            "instructors": reference.INSTRUCTORS,
            "courses": reference.COURSES,
        }[kind]
        if row.existing is None:
            resources.create(db, principal, resource, values)
        else:
            resources.update(
                db,
                principal,
                resource,
                row.existing.id,
                version=row.existing.version,
                values=values,
            )
    elif kind == "groups":
        assert batch.term_id is not None
        parent_code = values.pop("parent_code")
        if parent_code is not None:
            values["parent_id"] = created_groups.get(parent_code) or db.scalar(
                select(StudentGroup.id).where(
                    StudentGroup.term_id == batch.term_id,
                    func.upper(StudentGroup.code) == parent_code,
                )
            )
        else:
            values["parent_id"] = None
        if row.existing is None:
            group = group_service.create_group(db, principal, batch.term_id, values)
        else:
            group = group_service.update_group(
                db,
                principal,
                batch.term_id,
                row.existing.id,
                version=row.existing.version,
                values=values,
            )
        created_groups[(row.key or "").upper()] = group.id
    else:
        assert batch.term_id is not None
        activity_service.create_activity(db, principal, batch.term_id, values)


def template(entity_type: str) -> tuple[list[str], list[str]]:
    """Header labels and an example row for a blank import file."""
    spec = SPECS.get(entity_type)
    if spec is None:
        raise NotFound("Import template")
    return [c.label for c in spec.columns], [c.example for c in spec.columns]
