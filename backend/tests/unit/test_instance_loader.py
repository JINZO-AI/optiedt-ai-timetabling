"""The loader against the figures already verified in scripts/verify-instance.ps1.

If any of these numbers drift, either the instance changed (re-verify it and
update both this test and docs/status.md) or the loader has a bug. Either way
this test, not a guess, should be the one to notice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from optiedt.domain.enums import (
    AvailabilityState,
    ConstraintKind,
    DeclarationSource,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.instance.loader import load_instance

INSTANCE_PATH = Path(__file__).resolve().parents[3] / "data" / "instance"


@pytest.fixture(scope="module")
def instance():
    return load_instance(INSTANCE_PATH)


def test_counts_match_the_documented_instance(instance):
    assert len(instance.programmes) == 3
    assert len(instance.promotions) == 6
    assert len(instance.groups) == 51
    assert len(instance.teachers) == 44
    assert len(instance.courses) == 32
    assert len(instance.sessions) == 218
    assert len(instance.rooms) == 20
    assert len(instance.slots) == 30
    assert len(instance.availability) == 157
    assert len(instance.holidays) == 18
    assert len(instance.constraints) == 19


def test_sessions_by_type(instance):
    by_type = {t: 0 for t in SessionType}
    for s in instance.sessions:
        by_type[s.type] += 1
    assert by_type[SessionType.CM] == 32
    assert by_type[SessionType.TD] == 82
    assert by_type[SessionType.TP] == 104


def test_two_period_sessions_counted_correctly(instance):
    # 104 of 218 sessions span two periods — the reason y[s][t] must mean
    # "occupies t", not "starts at t" (C-7). Not exercised until Phase 3's
    # objective, but the loader must get the raw count right regardless.
    two_period = sum(1 for s in instance.sessions if s.duration_periods == 2)
    assert two_period == 104


def test_groups_by_level(instance):
    by_level = {lvl: 0 for lvl in GroupLevel}
    for g in instance.groups:
        by_level[g.level] += 1
    assert by_level[GroupLevel.PROMO] == 6
    assert by_level[GroupLevel.TD] == 15
    assert by_level[GroupLevel.TP] == 30


def test_rooms_by_type(instance):
    """2 / 7 / 8 / 3, not the 2 / 10 / 6 / 2 the specification first recorded.

    Three classrooms were re-typed as laboratories on 2026-07-30 because the
    original mix made the instance INFEASIBLE: all 104 laboratory sessions span
    two periods, and a two-period session must fit inside one day, so a room
    offers only 11 two-period windows a week (five 5-period days give two each,
    Saturday's 3 open periods give one). Six computer laboratories therefore
    offered 66 windows against 80 sessions. See C-13 in docs/open-questions.md.
    """
    by_type = {t: 0 for t in RoomType}
    for r in instance.rooms:
        by_type[r.type] += 1
    assert by_type[RoomType.AMPHI] == 2
    assert by_type[RoomType.SALLE] == 7
    assert by_type[RoomType.LAB_INFO] == 8
    assert by_type[RoomType.LAB_SCIENCES] == 3
    assert sum(by_type.values()) == 20, "the re-typing kept the total room count unchanged"


def test_teachers_by_rank(instance):
    by_rank = {r: 0 for r in TeacherRank}
    for t in instance.teachers:
        by_rank[t.rank] += 1
    assert by_rank[TeacherRank.PROFESSEUR] == 7
    assert by_rank[TeacherRank.MAITRE_DE_CONFERENCES] == 11
    assert by_rank[TeacherRank.MAITRE_ASSISTANT] == 13
    assert by_rank[TeacherRank.ASSISTANT] == 13


def test_open_slots(instance):
    assert len(instance.slots) == 30
    assert sum(1 for s in instance.slots if s.is_open) == 28


def test_promo_groups_have_no_parent(instance):
    for g in instance.groups:
        if g.level is GroupLevel.PROMO:
            assert g.parent_group is None
        else:
            assert g.parent_group is not None


def test_availability_all_synthetic_and_unavailable(instance):
    # All 157 rows are unavailability declarations (C-12: there is no
    # "preferred" state in this schema, though S5 has weight 0.20).
    assert len(instance.availability) == 157
    assert {a.source for a in instance.availability} == {DeclarationSource.SYNTHETIC}
    assert {a.state for a in instance.availability} == {AvailabilityState.UNAVAILABLE}


def test_availability_covers_41_of_44_teachers(instance):
    assert len({a.teacher for a in instance.availability}) == 41


def test_semester_parsed_from_the_s2_code(instance):
    # courses.csv and teacher_availability.csv encode "S2", a string; the
    # domain entities declare semester: int.
    assert {c.semester for c in instance.courses} == {2}
    assert {a.semester for a in instance.availability} == {2}


def test_lunar_holidays(instance):
    assert sum(1 for h in instance.holidays if h.lunar) == 10


def test_catalogue_hard_and_soft(instance):
    hard = [c for c in instance.constraints if c.kind is ConstraintKind.HARD]
    soft = [c for c in instance.constraints if c.kind is ConstraintKind.SOFT]
    assert len(hard) == 12
    assert len(soft) == 7
    assert round(sum(c.default_weight for c in soft), 4) == 0.90
    assert all(c.default_weight == 0.0 for c in hard)


def test_retired_codes_absent(instance):
    codes = {c.code for c in instance.constraints}
    assert not codes & {"S1", "S8", "S9"}


def test_calendar_config_loaded(instance):
    assert instance.calendar_config["periods_per_day"] == "5"
    assert instance.calendar_config["days_per_week"] == "6"


def test_missing_file_raises_with_the_filename(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"programmes\.csv"):
        load_instance(tmp_path)
