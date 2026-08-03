"""The in-application checks must agree with the standalone verifier.

**The two implementations are independent on purpose**, and that is exactly why
they need comparing. `data/verification/verify_instance.py` guards the contract
between the generator and the application, so it depends on neither side of it
— not on the domain entities, not on the loader, not on a third-party import.
`optiedt.preanalysis` reports the same arithmetic through the API. Same
definition, written twice.

Two implementations of one definition drift silently unless something compares
them numerically. `tests/integration/test_objective_matches_analysis.py` makes
that argument for the objective, where reading the two side by side missed a
28x scale error; the same argument applies here, and the consequence of a drift
would be worse — a structural-risk report that disagrees with the checker CI
runs is a report nobody can act on.

Figures are re-derived from the CSVs here rather than copied from
docs/data-and-instance.md. A constant transcribed from a document proves the
transcription, not the arithmetic — and this is the one project where a
verification table went stale for a day while certifying a room mix the
instance no longer had (C-11).
"""

from __future__ import annotations

import collections
import csv
from pathlib import Path

import pytest

from optiedt.domain.instance import Instance
from optiedt.instance.loader import load_instance
from optiedt.preanalysis.checks import (
    CHECK_GROUP_HIERARCHY,
    CHECK_ROOM_SUITABILITY,
    CHECK_SLOT_COVERAGE,
    CHECK_TEACHER_FREE_SLOTS,
    CHECK_TEACHER_LOAD,
    CheckResult,
)
from optiedt.preanalysis.verifications import DefaultPreAnalysis, coverage_by_type

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"


@pytest.fixture(scope="module")
def instance() -> Instance:
    return load_instance(INSTANCE_PATH)


@pytest.fixture(scope="module")
def results(instance: Instance) -> dict[str, CheckResult]:
    return {r.name: r for r in DefaultPreAnalysis().verify(instance)}


def _rows(name: str) -> list[dict[str, str]]:
    with (INSTANCE_PATH / name).open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


# ── All five pass on the reference instance ────────────────────────────


def test_all_five_pass_on_the_reference_instance(results: dict[str, CheckResult]) -> None:
    """What scripts/verify-instance.ps1 asserts, asserted through the product."""
    failing = [r for r in results.values() if not r.passed]
    assert not failing, "; ".join(f"{r.name}: {r.detail}" for r in failing)
    assert set(results) == {
        CHECK_ROOM_SUITABILITY,
        CHECK_SLOT_COVERAGE,
        CHECK_TEACHER_LOAD,
        CHECK_TEACHER_FREE_SLOTS,
        CHECK_GROUP_HIERARCHY,
    }


# ── Verification 2, both bounds, re-derived from the CSVs ──────────────


def _open_runs_from_csv() -> list[int]:
    by_day: dict[str, list[int]] = collections.defaultdict(list)
    for row in _rows("slots.csv"):
        if _truthy(row["is_open"]):
            by_day[row["day_index"]].append(int(row["slot_id"]))
    runs: list[int] = []
    for day_slots in by_day.values():
        length, previous = 0, None
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
    return runs


def test_period_occupancy_matches_the_raw_csvs(instance: Instance) -> None:
    open_slots = sum(1 for r in _rows("slots.csv") if _truthy(r["is_open"]))
    rooms = collections.Counter(r["room_type"] for r in _rows("rooms.csv"))
    required: collections.Counter[str] = collections.Counter()
    for row in _rows("sessions.csv"):
        required[row["required_room_type"]] += int(row["duration_periods"]) * int(
            row.get("occurrences_per_week", 1)
        )

    for coverage in coverage_by_type(instance):
        key = str(coverage.room_type)
        assert coverage.rooms == rooms[key]
        assert coverage.periods_required == required[key]
        assert coverage.periods_available == rooms[key] * open_slots


def test_two_period_window_supply_matches_the_raw_csvs(instance: Instance) -> None:
    """⚠️ The bound that binds. Reading the period figure alone let C-13 through."""
    runs = _open_runs_from_csv()
    per_room = sum(length // 2 for length in runs)
    rooms = collections.Counter(r["room_type"] for r in _rows("rooms.csv"))
    demand: collections.Counter[str] = collections.Counter()
    for row in _rows("sessions.csv"):
        if int(row["duration_periods"]) == 2:
            demand[row["required_room_type"]] += int(row.get("occurrences_per_week", 1))

    for coverage in coverage_by_type(instance):
        key = str(coverage.room_type)
        assert coverage.window_demand.get(2, 0) == demand[key]
        if demand[key]:
            assert coverage.window_supply[2] == rooms[key] * per_room


def test_the_tightest_point_is_computer_laboratories(instance: Instance) -> None:
    """90.9 % of two-period windows against 71.4 % of periods.

    Both figures are re-derived above; this asserts the RELATION between them,
    which is the fact worth pinning: the reassuring number and the binding
    number are different numbers, and the binding one is not the one a reader
    reaches for first.
    """
    by_type = {str(c.room_type): c for c in coverage_by_type(instance)}
    lab_info = by_type["Lab_Info"]

    assert lab_info.window_percent(2) > lab_info.period_percent
    assert lab_info.window_percent(2) > 90.0
    assert lab_info.period_percent < 80.0
    # 8 spare two-period windows in the whole week.
    assert lab_info.window_supply[2] - lab_info.window_demand[2] == 8
    assert max(c.window_percent(2) for c in by_type.values() if 2 in c.window_demand) == (
        lab_info.window_percent(2)
    )


def test_the_report_names_the_binding_resource(results: dict[str, CheckResult]) -> None:
    coverage = results[CHECK_SLOT_COVERAGE]
    assert coverage.passed
    assert "Lab_Info" in coverage.detail
    assert "binding resource" in coverage.detail


# ── Verifications 3 and 4, re-derived from the CSVs ────────────────────


def test_teacher_load_figures_match_the_raw_csvs(results: dict[str, CheckResult]) -> None:
    load: collections.Counter[str] = collections.Counter()
    for row in _rows("sessions.csv"):
        load[row["teacher_id"]] += int(row["duration_periods"]) * int(
            row.get("occurrences_per_week", 1)
        )
    heaviest = max(load.values())
    detail = results[CHECK_TEACHER_LOAD].detail
    assert f"heaviest load {heaviest} periods" in detail
    assert f"({heaviest * 1.5:g} h)" in detail


def test_teacher_free_slot_margin_matches_the_raw_csvs(results: dict[str, CheckResult]) -> None:
    open_slots = sum(1 for r in _rows("slots.csv") if _truthy(r["is_open"]))
    unavailable = collections.Counter(
        row["teacher_id"]
        for row in _rows("teacher_availability.csv")
        if not _truthy(row["is_available"])
    )
    load: collections.Counter[str] = collections.Counter()
    for row in _rows("sessions.csv"):
        load[row["teacher_id"]] += int(row["duration_periods"]) * int(
            row.get("occurrences_per_week", 1)
        )
    smallest = min(
        (open_slots - unavailable.get(t["teacher_id"], 0)) - load.get(t["teacher_id"], 0)
        for t in _rows("teachers.csv")
    )
    assert f"smallest margin {smallest} free slots" in results[CHECK_TEACHER_FREE_SLOTS].detail


# ── Verification 5, and the half that stays outside ────────────────────


def test_group_hierarchy_figures_match_the_raw_csvs(results: dict[str, CheckResult]) -> None:
    levels = collections.Counter(row["group_type"] for row in _rows("groups.csv"))
    detail = results[CHECK_GROUP_HIERARCHY].detail
    assert "0 invalid parent references, 0 invalid chains, 0 cycles" in detail
    for level, count in levels.items():
        assert f"{level} {count}" in detail


def test_the_student_half_is_declared_out_of_scope(results: dict[str, CheckResult]) -> None:
    """`Instance` excludes `Student`, so this check is narrower than the
    verifier's and must say so rather than pass for it."""
    assert "NOT checked here" in results[CHECK_GROUP_HIERARCHY].detail
