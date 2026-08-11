"""FR-1 — Load and manage the data of the department.

    Criterion (SRS §3.2, Table 4. FR-1. Data management), transcribed verbatim
    in docs/testing-strategy.md §4:

      Input       Files or forms validated by the server
      Processing  Verification of the types and of the references, then
                  recording
      Output      Entities recorded and report of the rejected lines

⚠️ **Verified against the §3.2 row, not against SRS Table 35 — which has no FR-1
row.** That is the same shape Phase 10 closed FR-4, FR-7, FR-14 and FR-16
against: the supervisor wrote an input/processing/output specification and no
acceptance test, so the §3.2 row *is* the promise. It is quoted above rather
than paraphrased, and nothing here was invented to fill a gap.

⚠️ **The A7 compatibility rule is a PROJECT DECISION**, recorded as such in
`docs/open-questions.md` (C-22) and `docs/decisions/ADR-012`. The supervisor did
not write it; it is derived from repository evidence. The tests that verify it
say so at their own head, so that a reader can tell the supervisor's promise
from the project's.

Everything here goes through the HTTP API, because a requirement is `✓` only
once a user can reach it.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping

import pytest

from optiedt.api import deps
from optiedt.domain.enums import AvailabilityState
from optiedt.instance.loader import resolve_instance_path
from optiedt.instance.validation import (
    AVAILABILITY,
    DEPARTMENT_FILES,
    GROUPS,
    ROOMS,
    SESSIONS,
    SLOTS,
    TEACHERS,
)
from optiedt.services.availability import build_declaration
from optiedt.services.calendar import CalendarOverrides

from .conftest import Application, FakeSolver, wire_application

pytestmark = pytest.mark.acceptance
"""⚠️ **`scripts/run-acceptance.ps1` selects by this MARKER, not by directory.**

Without it a file sits in `tests/acceptance/` and is still absent from the
suite that verifies requirements — it runs under `run-checks.ps1` and looks
green, while the one report that answers *"is FR-1 verified against its
criterion?"* never mentions it. This file was written without the marker and
was silently excluded for exactly that reason; the suite collected 197 where
the directory held 231, and the difference was FR-1.
"""


@pytest.fixture(scope="module")
def reference_files() -> dict[str, str]:
    root = resolve_instance_path("../data/instance")
    return {name: (root / name).read_text(encoding="utf-8-sig") for name in DEPARTMENT_FILES}


@pytest.fixture
def application() -> Iterator[Application]:
    """FR-1's criterion is about the application, so a fake solver is right.

    Whether CP-SAT can solve the imported dataset is FR-3's question; what this
    file verifies is that a supplied dataset is verified, recorded and reachable.
    One test does launch a run, to establish that the recorded dataset is what a
    run is actually assembled from - the fake places against whatever instance
    it is handed, which is precisely the fact under test.
    """
    solver = FakeSolver()
    with wire_application(lambda: solver) as wired:
        yield wired


def upload(files: Mapping[str, str]) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", (name, text.encode("utf-8"), "text/csv")) for name, text in files.items()]


def post(application: Application, files: Mapping[str, str]) -> dict[str, object]:
    response = application.client.post("/api/dataset", files=upload(files))
    assert response.status_code == 200, response.text
    return dict(response.json())


def set_field(
    files: Mapping[str, str], name: str, line_number: int, column: str, value: str
) -> dict[str, str]:
    lines = files[name].splitlines()
    index = lines[0].split(",").index(column)
    cells = lines[line_number - 1].split(",")
    cells[index] = value
    lines[line_number - 1] = ",".join(cells)
    return {**files, name: "\n".join(lines) + "\n"}


def drop_teacher(files: Mapping[str, str], teacher: str) -> dict[str, str]:
    """A dataset that no longer employs one teacher, and is otherwise whole.

    Their sessions and generated availability rows go too — otherwise the
    dataset fails the validator's own reference check and never reaches the
    compatibility question this helper exists to ask.
    """
    keep_rows = {
        TEACHERS: lambda line: not line.startswith(f"{teacher},"),
        SESSIONS: lambda line: f",{teacher}," not in line,
        AVAILABILITY: lambda line: f",{teacher}," not in line,
    }
    out = dict(files)
    for name, keep in keep_rows.items():
        lines = files[name].splitlines()
        out[name] = "\n".join([lines[0], *[ln for ln in lines[1:] if keep(ln)]]) + "\n"
    return out


def drop_slots_from(files: Mapping[str, str], first_dropped: int) -> dict[str, str]:
    slots = files[SLOTS].splitlines()
    kept = [ln for ln in slots[1:] if ln.strip() and int(ln.split(",")[0]) < first_dropped]
    rows = files[AVAILABILITY].splitlines()
    index = rows[0].split(",").index("slot_id")
    kept_rows = [ln for ln in rows[1:] if ln.strip() and int(ln.split(",")[index]) < first_dropped]
    return {
        **files,
        SLOTS: "\n".join([slots[0], *kept]) + "\n",
        AVAILABILITY: "\n".join([rows[0], *kept_rows]) + "\n",
    }


# ── Input: files validated by the server ───────────────────────────────


def test_a_department_dataset_is_supplied_as_files_and_recorded(
    application, reference_files
) -> None:
    """Input → Processing → Output, in one call: the criterion's whole shape."""
    outcome = post(application, reference_files)

    assert outcome["accepted"] is True
    assert outcome["rejectedLines"] == []
    assert outcome["incompatibilities"] == []
    assert outcome["dataset"]["imported"] is True
    assert outcome["dataset"]["sessions"] == 218
    assert outcome["dataset"]["rooms"] == 20


def test_before_any_import_the_reference_files_govern_and_say_so(application) -> None:
    """⚠️ "Not imported" must be distinguishable from "imported and identical".

    An installation reading `imported: true` when nobody has supplied anything
    would make the withdrawal button meaningless.
    """
    response = application.client.get("/api/dataset")

    assert response.status_code == 200
    body = response.json()
    assert body["imported"] is False
    assert body["importedBy"] is None
    assert body["sessions"] == 218, "the reference instance is in force"


def test_a_recorded_dataset_names_who_supplied_it_and_when(application, reference_files) -> None:
    post(application, reference_files)

    body = application.client.get("/api/dataset").json()

    assert body["imported"] is True
    assert body["importedBy"] == "acceptance"
    assert body["importedAt"] is not None
    assert sorted(body["files"]) == sorted(DEPARTMENT_FILES)


# ── Output: entities recorded ──────────────────────────────────────────


def test_the_recorded_entities_become_what_every_screen_reads(application, reference_files) -> None:
    """ "Entities recorded" is only true if they are the ones served afterwards."""
    smaller = drop_teacher(reference_files, "T044")

    post(application, smaller)

    instance = application.client.get("/api/instance").json()
    assert all(t["id"] != "T044" for t in instance["teachers"])
    assert len(instance["teachers"]) == 43


def test_the_recorded_dataset_is_what_a_run_is_assembled_from(application, reference_files) -> None:
    """⚠️ The strongest reachability statement available without a real solve:
    an imported dataset reaches the SOLVER's input, not merely the screens."""
    smaller = drop_teacher(reference_files, "T044")
    post(application, smaller)

    run = application.launch()

    assert run["state"] == "COMPLETED", run.get("error")
    candidate = run["candidates"][0]
    sessions = {p["session"] for p in candidate["placements"]}
    assert sessions, "the run placed the imported dataset's sessions"
    assert len(sessions) < 218, "T044's sessions are not in the dataset and were not placed"


def test_a_second_import_is_served_and_the_first_is_not(application, reference_files) -> None:
    """⚠️ **The staleness property, stated as a test rather than as a comment.**

    `base_instance()` reuses a parsed dataset only while the store's revision is
    unchanged, and the revision is read from the store on every call. Import one
    dataset, then a different one: the second must be what is served. A cache
    keyed by anything other than that revision passes the first import and fails
    here — which is exactly what mutation testing found it doing before this
    test existed.
    """
    post(application, drop_teacher(reference_files, "T044"))
    assert len(application.client.get("/api/instance").json()["teachers"]) == 43

    post(application, drop_teacher(drop_teacher(reference_files, "T044"), "T043"))

    served = application.client.get("/api/instance").json()["teachers"]
    assert len(served) == 42
    assert all(t["id"] not in {"T043", "T044"} for t in served)


def test_withdrawal_is_served_immediately_and_not_after_a_restart(
    application, reference_files
) -> None:
    """The same property in the other direction: a withdrawal must take effect
    on the next read, not on the next process."""
    post(application, drop_teacher(reference_files, "T044"))
    assert len(application.client.get("/api/instance").json()["teachers"]) == 43

    application.client.delete("/api/dataset")

    assert len(application.client.get("/api/instance").json()["teachers"]) == 44


def test_an_imported_dataset_survives_a_new_process(application, reference_files) -> None:
    """⚠️ Persistence checked by discarding the parse, not by trusting it.

    The in-process cache is keyed by the store's revision, so clearing it is
    exactly what a restart does to it: the next read must come back from the
    store. `test_store_contract` covers the same property against real
    PostgreSQL.
    """
    post(application, drop_teacher(reference_files, "T044"))

    deps._parsed_dataset.clear()

    assert len(deps.base_instance().teachers) == 43


# ── Processing: verification of the types ──────────────────────────────


def test_a_dataset_with_a_bad_type_is_refused_and_the_line_is_reported(
    application, reference_files
) -> None:
    outcome = post(application, set_field(reference_files, ROOMS, 2, "capacity", "grand"))

    assert outcome["accepted"] is False
    assert outcome["dataset"]["imported"] is False, "nothing was recorded"
    rejected = outcome["rejectedLines"]
    assert [(r["file"], r["line"], r["field"], r["value"]) for r in rejected] == [
        ("rooms.csv", 2, "capacity", "grand")
    ]


def test_a_missing_file_is_reported_rather_than_assumed_empty(application, reference_files) -> None:
    without = {k: v for k, v in reference_files.items() if k != ROOMS}

    outcome = post(application, without)

    assert outcome["accepted"] is False
    assert [(r["file"], r["line"]) for r in outcome["rejectedLines"]] == [("rooms.csv", None)]


def test_the_constraint_catalogue_cannot_be_supplied(application, reference_files) -> None:
    """⚠️ ADR-003 and invariant 7: the rule catalogue is the software's, not the
    department's. An upload that could replace it could delete a hard rule."""
    outcome = post(
        application,
        {**reference_files, "constraint_catalogue.csv": "code,name,kind\nH1,Invented,SOFT\n"},
    )

    assert outcome["accepted"] is False
    assert any(r["file"] == "constraint_catalogue.csv" for r in outcome["rejectedLines"])


def test_a_file_that_is_not_text_is_reported_rather_than_crashing(application) -> None:
    response = application.client.post(
        "/api/dataset", files=[("files", ("rooms.csv", b"\xff\xfe\x00\x01", "text/csv"))]
    )

    assert response.status_code == 200
    outcome = response.json()
    assert outcome["accepted"] is False
    assert any("UTF-8" in r["reason"] for r in outcome["rejectedLines"])


# ── Processing: verification of the references ─────────────────────────


def test_a_session_naming_a_teacher_nobody_declared_is_refused(
    application, reference_files
) -> None:
    outcome = post(application, set_field(reference_files, SESSIONS, 2, "teacher_id", "T999"))

    assert outcome["accepted"] is False
    rejected = outcome["rejectedLines"]
    assert len(rejected) == 1
    assert (rejected[0]["file"], rejected[0]["field"], rejected[0]["value"]) == (
        "sessions.csv",
        "teacher_id",
        "T999",
    )
    assert "teacher" in rejected[0]["reason"]


def test_a_group_hanging_off_a_group_nobody_declared_is_refused(
    application, reference_files
) -> None:
    outcome = post(application, set_field(reference_files, GROUPS, 2, "parent_group_id", "G999"))

    assert outcome["accepted"] is False
    assert [r["field"] for r in outcome["rejectedLines"]] == ["parent_group_id"]


def test_every_rejected_line_comes_back_in_one_report(application, reference_files) -> None:
    """⚠️ Not one per attempt. A hundred-row correction must not cost a hundred
    round trips, which is what "report of the rejected lines" is for."""
    broken = set_field(reference_files, ROOMS, 2, "capacity", "x")
    broken = set_field(broken, TEACHERS, 2, "rank", "Recteur")
    broken = set_field(broken, SLOTS, 2, "is_open", "peut-etre")

    outcome = post(application, broken)

    assert {r["file"] for r in outcome["rejectedLines"]} == {
        "rooms.csv",
        "teachers.csv",
        "slots.csv",
    }


def test_every_broken_reference_comes_back_in_one_report(application, reference_files) -> None:
    broken = set_field(reference_files, SESSIONS, 2, "teacher_id", "T999")
    broken = set_field(broken, GROUPS, 2, "parent_group_id", "G999")
    broken = set_field(broken, AVAILABILITY, 2, "slot_id", "999")

    outcome = post(application, broken)

    assert {r["file"] for r in outcome["rejectedLines"]} == {
        "groups.csv",
        "sessions.csv",
        "teacher_availability.csv",
    }


def test_the_report_says_when_the_references_were_not_reached_yet(
    application, reference_files
) -> None:
    """⚠️ **A staged report, and the response says so rather than leaving a user
    to discover a second round.**

    References are examined only once every line parses, because a rejected line
    takes its identifier with it: a session naming a teacher whose own row
    failed to parse would be reported as an unknown reference too — one defect,
    two reports, the second vanishing when the first is fixed. That is a
    deliberate choice, and `referencesChecked` is what stops the interface
    having to guess whether the list is complete.
    """
    parses = post(application, set_field(reference_files, SESSIONS, 2, "teacher_id", "T999"))
    does_not_parse = post(application, set_field(reference_files, ROOMS, 2, "capacity", "x"))

    assert parses["referencesChecked"] is True
    assert does_not_parse["referencesChecked"] is False


def test_an_accepted_import_reports_that_everything_was_checked(
    application, reference_files
) -> None:
    assert post(application, reference_files)["referencesChecked"] is True


# ── Atomicity: either all of it, or none of it ─────────────────────────


def test_one_bad_line_records_nothing_at_all(application, reference_files) -> None:
    outcome = post(application, set_field(reference_files, ROOMS, 2, "capacity", "x"))

    assert outcome["accepted"] is False
    assert application.client.get("/api/dataset").json()["imported"] is False


def test_a_refused_replacement_leaves_the_previous_dataset_in_force(
    application, reference_files
) -> None:
    """⚠️ *"The existing dataset remains active when compatibility validation
    fails"* — and the same holds for a validation failure. Checked on the
    CONTENT served afterwards, not only on the flag."""
    post(application, drop_teacher(reference_files, "T044"))
    assert len(application.client.get("/api/instance").json()["teachers"]) == 43

    outcome = post(application, set_field(reference_files, ROOMS, 2, "capacity", "x"))

    assert outcome["accepted"] is False
    assert outcome["dataset"]["teachers"] == 43, "the response describes what is in force"
    assert len(application.client.get("/api/instance").json()["teachers"]) == 43


# ── A7 — the project decision. Not the supervisor's wording ────────────


def test_a_replacement_that_would_orphan_a_declaration_is_refused(
    application, reference_files
) -> None:
    """> **Project decision — determined from repository evidence and
    > engineering research because supervisor clarification was unavailable.**
    >
    > A dataset replacement must be rejected if it would leave existing
    > persisted FR-2 declarations or FR-9 calendar overrides invalid or
    > orphaned.

    ⚠️ Nothing in the specification says this. See ADR-012 and C-22.
    """
    deps.get_availability_store().declare(
        "T044",
        build_declaration(teacher="T044", semester=2, cells={13: AvailabilityState.UNAVAILABLE}),
    )

    outcome = post(application, drop_teacher(reference_files, "T044"))

    assert outcome["accepted"] is False
    assert outcome["rejectedLines"] == [], "the file is correct; the installation is not"
    found = outcome["incompatibilities"]
    assert [(i["overlay"], i["subject"]) for i in found] == [("availability", "T044")]
    assert "clear that declaration first" in found[0]["remedy"]


def test_a_refused_replacement_deletes_no_declaration(application, reference_files) -> None:
    """*"Existing overlay data must not be silently deleted."*"""
    store = deps.get_availability_store()
    store.declare(
        "T044",
        build_declaration(teacher="T044", semester=2, cells={13: AvailabilityState.UNAVAILABLE}),
    )

    post(application, drop_teacher(reference_files, "T044"))

    assert store.declared_teachers() == frozenset({"T044"})
    assert store.declarations("T044") == build_declaration(
        teacher="T044", semester=2, cells={13: AvailabilityState.UNAVAILABLE}
    )


def test_clearing_the_declaration_first_lets_the_replacement_through(
    application, reference_files
) -> None:
    """⚠️ **The escape route, and A7 would deadlock without it.**

    No endpoint forgets a declaration. What the person in charge can do is empty
    that teacher's grid — `_require_own_grid` returns early for every role but
    TEACHER — and an emptied grid contributes no availability row. Compatibility
    is judged on the effective rows rather than on `declared_teachers()`, which
    is exactly what keeps this path open.
    """
    store = deps.get_availability_store()
    store.declare(
        "T044",
        build_declaration(teacher="T044", semester=2, cells={13: AvailabilityState.UNAVAILABLE}),
    )
    assert post(application, drop_teacher(reference_files, "T044"))["accepted"] is False

    response = application.client.put(
        "/api/teachers/T044/availability", json={"semester": 2, "cells": []}
    )
    assert response.status_code == 200, response.text

    assert "T044" in store.declared_teachers(), "the marker survives; it is inert"
    assert post(application, drop_teacher(reference_files, "T044"))["accepted"] is True


def test_a_replacement_that_would_orphan_a_closure_is_refused(application, reference_files) -> None:
    """⚠️ The FR-9 half, and it cannot be folded into the FR-2 half: an orphaned
    closure leaves no trace in the effective dataset, because `apply_calendar`
    consults only the slots the new dataset has. See `unit/test_dataset.py`."""
    deps.get_calendar_store().save(
        CalendarOverrides(slot_open=((27, False),)), author="administrateur"
    )

    outcome = post(application, drop_slots_from(reference_files, 25))

    assert outcome["accepted"] is False
    found = outcome["incompatibilities"]
    assert [(i["overlay"], i["subject"]) for i in found] == [("calendar", "27")]
    assert "DELETE /api/calendar" in found[0]["remedy"]


def test_a_refused_replacement_deletes_no_closure(application, reference_files) -> None:
    store = deps.get_calendar_store()
    stated = CalendarOverrides(slot_open=((27, False),))
    store.save(stated, author="administrateur")

    post(application, drop_slots_from(reference_files, 25))

    assert store.overrides() == stated
    assert store.last_edit() is not None


def test_a_replacement_keeping_what_is_stated_is_accepted(application, reference_files) -> None:
    """The rule refuses orphaning, not change. A dataset that keeps slot 7 and
    teacher T001 goes through with both statements still in force."""
    deps.get_availability_store().declare(
        "T001",
        build_declaration(teacher="T001", semester=2, cells={13: AvailabilityState.UNAVAILABLE}),
    )
    deps.get_calendar_store().save(
        CalendarOverrides(slot_open=((7, False),)), author="administrateur"
    )

    outcome = post(application, drop_teacher(reference_files, "T044"))

    assert outcome["accepted"] is True
    assert deps.get_calendar_store().overrides().slot_open == ((7, False),)


# ── Withdrawal is a replacement too ────────────────────────────────────


def test_withdrawing_an_import_restores_the_reference_dataset(application, reference_files) -> None:
    post(application, drop_teacher(reference_files, "T044"))
    assert len(application.client.get("/api/instance").json()["teachers"]) == 43

    response = application.client.delete("/api/dataset")

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert application.client.get("/api/dataset").json()["imported"] is False
    assert len(application.client.get("/api/instance").json()["teachers"]) == 44


def test_withdrawal_is_checked_for_compatibility_like_any_replacement(
    application, reference_files
) -> None:
    """⚠️ **A7, refinement 9.** Withdrawal changes the base, so it can orphan a
    statement exactly as an import can — here, a declaration for a teacher the
    imported dataset added and `data/instance/` does not have. Skipping the
    check here would leave a hole the size of the undo button.
    """
    with_new_teacher = {
        **reference_files,
        TEACHERS: reference_files[TEACHERS].rstrip("\n")
        + "\nT900,Nadia,Cherif,Informatique,Assistant,24,nadia.cherif@fac.tn\n",
    }
    assert post(application, with_new_teacher)["accepted"] is True
    deps.get_availability_store().declare(
        "T900",
        build_declaration(teacher="T900", semester=2, cells={13: AvailabilityState.UNAVAILABLE}),
    )

    response = application.client.delete("/api/dataset")

    assert response.status_code == 200
    outcome = response.json()
    assert outcome["accepted"] is False
    assert [i["subject"] for i in outcome["incompatibilities"]] == ["T900"]
    assert application.client.get("/api/dataset").json()["imported"] is True


def test_withdrawing_when_nothing_was_imported_is_not_an_error(application) -> None:
    response = application.client.delete("/api/dataset")

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["dataset"]["imported"] is False


# ── Rights: SRS Table 2, and C-8 ───────────────────────────────────────


@pytest.mark.parametrize("role", ["TEACHER", "ADMINISTRATOR", "STUDENT"])
def test_only_the_person_in_charge_may_read_or_replace_the_data(reference_files, role: str) -> None:
    """⚠️ **The administrator is refused, and that is not an oversight.**
    CdC §4.3 and SRS §3.3 both say the administrator loads the data; **SRS
    Table 2 gives it to the person in charge** and limits the administrator to
    accounts and the calendar. C-8 settled that Table 2 wins.
    """
    solver = FakeSolver()
    with wire_application(lambda: solver, role=role) as wired:
        assert wired.client.get("/api/dataset").status_code == 403
        assert wired.client.post("/api/dataset", files=upload(reference_files)).status_code == 403
        assert wired.client.delete("/api/dataset").status_code == 403


def test_the_person_in_charge_may(application) -> None:
    """The positive half — otherwise the test above would pass with the route
    forbidden to everyone."""
    assert application.client.get("/api/dataset").status_code == 200


def test_an_anonymous_caller_reaches_nothing(reference_files) -> None:
    from fastapi.testclient import TestClient

    from optiedt.api.main import app

    with TestClient(app) as client:
        assert client.get("/api/dataset").status_code == 401
        assert client.post("/api/dataset", files=upload(reference_files)).status_code == 401
        assert client.delete("/api/dataset").status_code == 401
