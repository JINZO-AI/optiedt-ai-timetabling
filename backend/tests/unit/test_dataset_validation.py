"""FR-1 — the verification of the types and of the references.

    SRS §3.2, Table 4. FR-1. Data management:
      Input       Files or forms validated by the server
      Processing  Verification of the types and of the references, then
                  recording
      Output      Entities recorded and report of the rejected lines

These tests are about the middle column and the second half of the third. The
first column is `tests/acceptance/test_fr01.py`, which drives it through the API.

⚠️ **The reference dataset is the fixture**, mutated one field at a time. A
hand-written miniature would be easier to read and would prove less: the files
this application is verified against are the ones it must accept, and a
validator that accepted a toy while rejecting `data/instance/` would pass a
suite built on toys.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from optiedt.instance.loader import load_instance, resolve_instance_path
from optiedt.instance.validation import (
    AVAILABILITY,
    CALENDAR_CONFIG,
    DEPARTMENT_FILES,
    GROUPS,
    HOLIDAYS,
    PROMOTIONS,
    ROOMS,
    SESSIONS,
    SLOTS,
    TEACHERS,
    RejectedLine,
    validate_dataset,
)


@pytest.fixture(scope="module")
def instance_root() -> Path:
    return resolve_instance_path("../data/instance")


@pytest.fixture(scope="module")
def catalogue(instance_root: Path):  # type: ignore[no-untyped-def]
    """The application's own constraint catalogue — never part of a dataset."""
    return load_instance(instance_root).constraints


@pytest.fixture(scope="module")
def reference_files(instance_root: Path) -> dict[str, str]:
    return {
        name: (instance_root / name).read_text(encoding="utf-8-sig") for name in DEPARTMENT_FILES
    }


def edited(
    files: Mapping[str, str], name: str, change: Callable[[list[str]], list[str]]
) -> dict[str, str]:
    """A copy of the dataset with one file's lines transformed."""
    lines = files[name].splitlines()
    return {**files, name: "\n".join(change(lines)) + "\n"}


def set_field(
    files: Mapping[str, str], name: str, line_number: int, column: str, value: str
) -> dict[str, str]:
    """One cell of one line, addressed by COLUMN NAME.

    ⚠️ By name rather than by position deliberately: several of these files
    carry columns the application does not read (`teachers.csv` has
    `first_name`, `slots.csv` has `day_name`), so a positional edit silently
    changes the wrong field and the test then passes for the wrong reason.
    """
    lines = files[name].splitlines()
    index = lines[0].split(",").index(column)
    cells = lines[line_number - 1].split(",")
    cells[index] = value
    lines[line_number - 1] = ",".join(cells)
    return {**files, name: "\n".join(lines) + "\n"}


def only(rejected: tuple[RejectedLine, ...], file: str) -> list[RejectedLine]:
    return [r for r in rejected if r.file == file]


# ── The dataset the application is verified against ────────────────────


def test_the_reference_dataset_is_accepted_whole(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    result = validate_dataset(reference_files, catalogue)

    assert result.rejected == ()
    assert result.accepted


def test_it_builds_exactly_what_the_loader_builds(  # type: ignore[no-untyped-def]
    reference_files, catalogue, instance_root
) -> None:
    """The strongest statement available: two parse paths, one result.

    ⚠️ Equality of the whole frozen `Instance`, not of a few counts. If the
    validator read a column differently from `instance/loader.py` — a semester,
    a boolean, an equipment flag — this fails, and the application would
    otherwise solve a dataset that was not the one on disk.
    """
    result = validate_dataset(reference_files, catalogue)

    assert result.instance == load_instance(instance_root)


# ── Files ──────────────────────────────────────────────────────────────


def test_a_missing_file_is_reported_against_the_file_not_a_line(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    without = {k: v for k, v in reference_files.items() if k != ROOMS}

    result = validate_dataset(without, catalogue)

    assert not result.accepted
    assert [(r.file, r.line) for r in result.rejected] == [(ROOMS, None)]
    assert "missing" in result.rejected[0].reason


def test_every_missing_file_is_named_at_once(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """Not one per attempt — the whole point of a report."""
    result = validate_dataset({SLOTS: reference_files[SLOTS]}, catalogue)

    assert {r.file for r in result.rejected} == set(DEPARTMENT_FILES) - {SLOTS}


def test_the_constraint_catalogue_is_refused_rather_than_ignored(  # type: ignore[no-untyped-def]
    reference_files, catalogue
) -> None:
    """ADR-003 and invariant 7: an upload may not touch the rule catalogue.

    ⚠️ **Refused, not silently dropped.** Dropping it would leave whoever sent
    it believing H1 to H12 had been replaced by their file.
    """
    with_catalogue = {**reference_files, "constraint_catalogue.csv": "code,name\nH99,Invented\n"}

    result = validate_dataset(with_catalogue, catalogue)

    assert not result.accepted
    rejected = only(result.rejected, "constraint_catalogue.csv")
    assert len(rejected) == 1
    assert "not part of a department dataset" in rejected[0].reason


def test_the_catalogue_comes_from_the_application_and_not_from_the_dataset(
    reference_files,  # type: ignore[no-untyped-def]
    catalogue,  # type: ignore[no-untyped-def]
) -> None:
    result = validate_dataset(reference_files, catalogue)

    assert result.instance is not None
    assert result.instance.constraints == catalogue
    assert {c.code for c in result.instance.constraints} >= {f"H{n}" for n in range(1, 13)}


def test_an_empty_file_is_reported_once(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    result = validate_dataset({**reference_files, HOLIDAYS: ""}, catalogue)

    assert [r.reason for r in only(result.rejected, HOLIDAYS)] == [
        "the file is empty; a header line is required"
    ]


def test_a_missing_column_is_one_rejection_not_one_per_row(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """20 rooms, one missing column, one line in the report."""
    broken = edited(
        reference_files, ROOMS, lambda ls: [ls[0].replace("capacity", "seats"), *ls[1:]]
    )

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, ROOMS)
    assert len(rejected) == 1
    assert rejected[0].line == 1
    assert "capacity" in rejected[0].reason


def test_a_column_declared_twice_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = edited(reference_files, ROOMS, lambda ls: [ls[0] + ",capacity", *ls[1:]])

    result = validate_dataset(broken, catalogue)

    assert "more than once" in only(result.rejected, ROOMS)[0].reason


# ── Rows and types ─────────────────────────────────────────────────────


def test_a_row_with_the_wrong_number_of_fields_names_its_line(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = edited(reference_files, ROOMS, lambda ls: [*ls[:3], ls[3] + ",extra", *ls[4:]])

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, ROOMS)
    assert len(rejected) == 1
    assert rejected[0].line == 4


def test_a_blank_line_is_not_a_fault(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """A trailing newline or a separator line is formatting, not data."""
    padded = edited(reference_files, HOLIDAYS, lambda ls: [*ls, "", ""])

    assert validate_dataset(padded, catalogue).accepted


def test_an_invalid_type_names_the_field_the_line_and_the_value(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, ROOMS, 2, "capacity", "grand")

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, ROOMS)
    assert len(rejected) == 1
    assert (rejected[0].line, rejected[0].field, rejected[0].value) == (2, "capacity", "grand")
    assert "whole number" in rejected[0].reason


def test_an_unknown_enum_value_lists_what_is_admitted(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, ROOMS, 2, "room_type", "Gymnase")

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, ROOMS)[0]
    assert rejected.field == "room_type"
    assert "Amphi" in rejected.reason and "Lab_Info" in rejected.reason


def test_an_unparsable_hour_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, SLOTS, 2, "start_time", "8h30")

    result = validate_dataset(broken, catalogue)

    assert only(result.rejected, SLOTS)[0].field == "start_time"


def test_an_unparsable_date_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, HOLIDAYS, 2, "holiday_date", "15/10/2025")

    result = validate_dataset(broken, catalogue)

    assert only(result.rejected, HOLIDAYS)[0].field == "holiday_date"


def test_a_word_that_is_not_a_boolean_is_refused_rather_than_read_as_false(
    reference_files,  # type: ignore[no-untyped-def]
    catalogue,  # type: ignore[no-untyped-def]
) -> None:
    """⚠️ This is where the validator is deliberately stricter than the loader.

    `instance/loader.py::_flag` treats every unrecognised string as false, which
    is right for files this repository generates and wrong for a file somebody
    typed: `is_open = "yes"` would silently close a slot that was meant to be
    open, and the timetable would be wrong rather than absent.
    """
    broken = set_field(reference_files, SLOTS, 2, "is_open", "yes")

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, SLOTS)[0]
    assert (rejected.field, rejected.value) == ("is_open", "yes")


@pytest.mark.parametrize("written", ["S2", "2"])
def test_a_semester_is_read_either_way_round(reference_files, catalogue, written: str) -> None:  # type: ignore[no-untyped-def]
    edited_files = set_field(reference_files, AVAILABILITY, 2, "semester", written)

    result = validate_dataset(edited_files, catalogue)

    assert only(result.rejected, AVAILABILITY) == []
    assert result.instance is not None


def test_a_semester_that_is_neither_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, AVAILABILITY, 2, "semester", "printemps")

    assert only(validate_dataset(broken, catalogue).rejected, AVAILABILITY)[0].field == "semester"


def test_a_required_value_left_empty_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, TEACHERS, 2, "department", "")

    rejected = only(validate_dataset(broken, catalogue).rejected, TEACHERS)[0]
    assert (rejected.field, rejected.reason) == ("department", "a value is required")


# ── Values the domain constrains ───────────────────────────────────────


def test_a_room_seating_nobody_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, ROOMS, 2, "capacity", "0")

    assert only(validate_dataset(broken, catalogue).rejected, ROOMS)[0].field == "capacity"


def test_a_session_longer_than_two_periods_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """C-7 and H8: one or two periods, and a two-period session fits one day.

    Nothing computes a window supply for a three-period session, so the
    pre-analysis would under-report and the solver would over-promise.
    """
    broken = set_field(reference_files, SESSIONS, 2, "duration_periods", "3")

    rejected = only(validate_dataset(broken, catalogue).rejected, SESSIONS)[0]
    assert (rejected.field, rejected.value) == ("duration_periods", "3")


def test_a_session_happening_zero_times_a_week_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, SESSIONS, 2, "occurrences_per_week", "0")

    assert (
        only(validate_dataset(broken, catalogue).rejected, SESSIONS)[0].field
        == "occurrences_per_week"
    )


def test_a_slot_ending_before_it_starts_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, SLOTS, 2, "end_time", "07:00")

    assert only(validate_dataset(broken, catalogue).rejected, SLOTS)[0].field == "end_time"


# ── Duplicate identifiers ──────────────────────────────────────────────


def test_a_repeated_identifier_rejects_the_second_line_and_names_the_first(
    reference_files,  # type: ignore[no-untyped-def]
    catalogue,  # type: ignore[no-untyped-def]
) -> None:
    """⚠️ The line a person must go and look at is the duplicate, not the
    original — so the report names the second and points back at the first."""
    broken = edited(reference_files, ROOMS, lambda ls: [*ls, ls[1]])

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, ROOMS)
    assert len(rejected) == 1
    assert rejected[0].line == len(reference_files[ROOMS].splitlines()) + 1
    assert "already declared on line 2" in rejected[0].reason


def test_a_repeated_slot_index_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = edited(reference_files, SLOTS, lambda ls: [*ls, ls[1]])

    assert only(validate_dataset(broken, catalogue).rejected, SLOTS)[0].field == "slot_id"


def test_a_repeated_configuration_key_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = edited(reference_files, CALENDAR_CONFIG, lambda ls: [*ls, "periods_per_day,7"])

    rejected = only(validate_dataset(broken, catalogue).rejected, CALENDAR_CONFIG)[0]
    assert (rejected.field, rejected.value) == ("key", "periods_per_day")


# ── References ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("file", "field", "what"),
    [
        (SESSIONS, "course_id", "course"),
        (SESSIONS, "group_id", "group"),
        (SESSIONS, "teacher_id", "teacher"),
        (PROMOTIONS, "programme_id", "programme"),
        (GROUPS, "parent_group_id", "group"),
        (AVAILABILITY, "teacher_id", "teacher"),
    ],
)
def test_a_reference_to_something_absent_is_refused(  # type: ignore[no-untyped-def]
    reference_files, catalogue, file: str, field: str, what: str
) -> None:
    broken = set_field(reference_files, file, 2, field, "NOWHERE")

    result = validate_dataset(broken, catalogue)

    rejected = only(result.rejected, file)
    assert len(rejected) == 1
    assert (rejected[0].line, rejected[0].field, rejected[0].value) == (2, field, "NOWHERE")
    assert what in rejected[0].reason


def test_an_availability_row_naming_a_slot_that_does_not_exist_is_refused(
    reference_files,  # type: ignore[no-untyped-def]
    catalogue,  # type: ignore[no-untyped-def]
) -> None:
    broken = set_field(reference_files, AVAILABILITY, 2, "slot_id", "999")

    rejected = only(validate_dataset(broken, catalogue).rejected, AVAILABILITY)[0]
    assert (rejected.field, rejected.value) == ("slot_id", "999")


def test_a_session_requiring_a_room_type_no_room_has_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """H4 restricts a session to rooms of its type; a type nobody has leaves it
    with an empty domain, and the run reports INFEASIBLE with no data fault
    named. Caught at the door instead."""
    without_labs = edited(
        reference_files,
        ROOMS,
        lambda ls: [ls[0], *[line for line in ls[1:] if "Lab_Sciences" not in line]],
    )

    result = validate_dataset(without_labs, catalogue)

    rejected = only(result.rejected, SESSIONS)
    assert rejected, "a session still requires Lab_Sciences"
    assert all(r.field == "required_room_type" for r in rejected)


def test_a_group_that_is_its_own_ancestor_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """⚠️ A cycle is checked here rather than left to FR-12 because
    `solver/constraints/overlap.py::_ancestor_chain` would not terminate, and
    `tasks/executor.py` does not stop a run when a check fails."""

    def make_cycle(lines: list[str]) -> list[str]:
        first = lines[1].split(",")
        second = lines[2].split(",")
        first[2] = second[0]  # parent := the next group
        second[2] = first[0]  # whose parent := the first
        return [lines[0], ",".join(first), ",".join(second), *lines[3:]]

    broken = edited(reference_files, GROUPS, make_cycle)
    rows = [line.split(",") for line in broken[GROUPS].splitlines()[1:] if line.strip()]
    parent_of = {row[0]: (row[2] or None) for row in rows}

    result = validate_dataset(broken, catalogue)

    cycles = {r.value for r in only(result.rejected, GROUPS) if "own ancestor" in r.reason}

    # ⚠️ NOT just the two groups in the loop. `_ancestor_chain` walks upwards
    # from every group, so every DESCENDANT of the cycle reaches it too - and
    # each of those is a session set whose H12 walk would never terminate. The
    # expected set is computed here rather than written as a number, so this
    # states the rule instead of recording today's instance.
    def reaches_cycle(group: str) -> bool:
        seen: set[str] = set()
        current: str | None = group
        while current is not None and current in parent_of:
            if current in seen:
                return True
            seen.add(current)
            current = parent_of[current]
        return False

    expected = {parent_of[g] for g in parent_of if reaches_cycle(g)}
    assert cycles == expected
    assert len(cycles) > 2, "the cycle is above 11 descendants; all of them hang the walk"
    assert not result.accepted


def test_references_are_checked_across_the_whole_dataset_not_in_file_order(
    reference_files,  # type: ignore[no-untyped-def]
    catalogue,  # type: ignore[no-untyped-def]
) -> None:
    """A session may name a course declared on a later line. Order is not meaning."""
    reversed_courses = edited(reference_files, "courses.csv", lambda ls: [ls[0], *reversed(ls[1:])])

    assert validate_dataset(reversed_courses, catalogue).accepted


# ── The report is a report ─────────────────────────────────────────────


def test_it_does_not_stop_at_the_first_rejected_line(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """Three faults in three files come back as three lines, in one pass."""
    broken = set_field(reference_files, ROOMS, 2, "capacity", "x")
    broken = set_field(broken, SLOTS, 2, "start_time", "x")
    broken = set_field(broken, TEACHERS, 2, "rank", "Recteur")

    result = validate_dataset(broken, catalogue)

    assert {r.file for r in result.rejected} == {ROOMS, SLOTS, TEACHERS}


def test_several_faults_in_one_file_are_all_reported(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, ROOMS, 2, "capacity", "x")
    broken = set_field(broken, ROOMS, 3, "capacity", "y")
    broken = set_field(broken, ROOMS, 4, "room_type", "Gymnase")

    result = validate_dataset(broken, catalogue)

    assert [r.line for r in only(result.rejected, ROOMS)] == [2, 3, 4]


def test_the_report_is_ordered_by_file_then_line(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, SLOTS, 2, "start_time", "x")
    broken = set_field(broken, TEACHERS, 2, "max_hours_per_week", "x")

    files = [r.file for r in validate_dataset(broken, catalogue).rejected]

    assert files == [TEACHERS, SLOTS], "DEPARTMENT_FILES order: teachers before slots"


def test_a_rejection_describes_itself_with_its_location(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    broken = set_field(reference_files, ROOMS, 2, "capacity", "grand")

    described = validate_dataset(broken, catalogue).rejected[0].describe()

    assert described.startswith("rooms.csv:2 [capacity] — ")


# ── Nothing partial ────────────────────────────────────────────────────


def test_one_bad_row_yields_no_instance_at_all(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """⚠️ The atomicity rule at its source: this type never offers "the good
    rows", so no caller can record them. 217 valid sessions do not become a
    dataset because one line was mistyped."""
    broken = set_field(reference_files, SESSIONS, 2, "duration_periods", "x")

    result = validate_dataset(broken, catalogue)

    assert result.instance is None
    assert not result.accepted


def test_a_dataset_with_no_session_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    empty = edited(reference_files, SESSIONS, lambda ls: [ls[0]])

    result = validate_dataset(empty, catalogue)

    assert [(r.file, r.line) for r in only(result.rejected, SESSIONS)] == [(SESSIONS, None)]


def test_a_dataset_with_no_room_is_refused(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    empty = edited(reference_files, ROOMS, lambda ls: [ls[0]])

    assert not validate_dataset(empty, catalogue).accepted


def test_a_dataset_may_legitimately_declare_no_holiday(reference_files, catalogue) -> None:  # type: ignore[no-untyped-def]
    """An institution with no holidays is a statement, not an omission —
    the same distinction `services/calendar.py` protects for FR-9."""
    none = edited(reference_files, HOLIDAYS, lambda ls: [ls[0]])

    result = validate_dataset(none, catalogue)

    assert result.accepted
    assert result.instance is not None
    assert result.instance.holidays == ()
