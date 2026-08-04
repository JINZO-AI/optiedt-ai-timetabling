"""Shared fixtures.

``tiny_instance`` is deliberately small enough that every criterion's value can
be computed by hand, and is used by two suites that must agree:
tests/unit/test_criteria.py (the analysis-layer formulas) and
tests/integration/test_objective_matches_analysis.py (the CP-SAT encoding of
the same formulas). Sharing one instance is the point - the two layers are
independent implementations of one definition (docs/open-questions.md, C-4),
so a fixture they both consume is what makes drift between them visible.
"""

from __future__ import annotations

import os
from datetime import time

import pytest

# ⚠️ Every test runs against IN-MEMORY stores unless it asks for a database.
#
# Set before anything imports `optiedt.core.config`, because `get_settings()`
# is lru_cached and the first call wins.
#
# This is not tidiness. When `persistence` began defaulting to "database" on
# 2026-08-04, `test_availability_api.py` kept passing and quietly wrote two
# rows into the developer's own database: it clears the dependency cache but
# does not override the store. A green suite that depends on PostgreSQL being
# up, and mutates it as a side effect, is worse than a failing one - it hides
# both facts. Tests that mean to exercise the database say so with
# `@pytest.mark.database` and take an explicit session factory.
os.environ.setdefault("OPTIEDT_PERSISTENCE", "memory")


from optiedt.domain.entities import (
    ConstraintDefinition,
    Course,
    Group,
    Programme,
    Promotion,
    Room,
    Session,
    Slot,
    Teacher,
)
from optiedt.domain.enums import (
    ConstraintKind,
    GroupLevel,
    RoomType,
    SessionType,
    TeacherRank,
)
from optiedt.domain.instance import Instance


@pytest.fixture
def signed_in():
    """Make every request from `app` come from a given account (FR-11).

    Used as `signed_in("PERSON_IN_CHARGE")` or `signed_in("TEACHER", "T001")`.

    ⚠️ This overrides the dependency rather than minting a real token, and the
    distinction matters: it lets a test about the WIRE FORMAT or about FR-2's
    replace-wholesale rule stay about that, instead of acquiring a sign-in it
    does not care about. Authentication itself, and every rule about who may do
    what, is tested for real against real tokens in
    `tests/integration/test_rbac.py` — overriding the dependency there would
    test the override.
    """
    from optiedt.api import deps
    from optiedt.api.main import app
    from optiedt.domain.entities import User
    from optiedt.domain.enums import UserRole

    def sign_in(role: str = "PERSON_IN_CHARGE", teacher: str | None = None) -> None:
        app.dependency_overrides[deps.current_user] = lambda: User(
            id="test-user", username="test", role=UserRole(role), teacher=teacher
        )

    yield sign_in
    app.dependency_overrides.pop(deps.current_user, None)


PERIODS_PER_DAY = 5
# Same shape as the reference calendar, so the noon-straddling period (index 2,
# 11:50-13:20) is found by the same derivation rather than by a magic number.
PERIOD_HOURS = [
    (time(8, 30), time(10, 0)),
    (time(10, 10), time(11, 40)),
    (time(11, 50), time(13, 20)),
    (time(14, 0), time(15, 30)),
    (time(15, 40), time(17, 10)),
]


def tiny_slots(days: int = 2) -> tuple[Slot, ...]:
    return tuple(
        Slot(
            index=day * PERIODS_PER_DAY + period,
            day_index=day,
            period_index=period,
            start_hour=PERIOD_HOURS[period][0],
            end_hour=PERIOD_HOURS[period][1],
            is_open=True,
        )
        for day in range(days)
        for period in range(PERIODS_PER_DAY)
    )


def tiny_session(sid: str, group: str, teacher: str, course: str, duration: int = 1) -> Session:
    return Session(
        id=sid,
        course=course,
        group=group,
        teacher=teacher,
        type=SessionType.TD,
        duration_periods=duration,
        occurrences_per_week=1,
        required_room_type=RoomType.SALLE,
        locked=False,
    )


@pytest.fixture
def tiny_instance() -> Instance:
    """One promotion P -> one TD group G -> one TP subgroup T (the only leaf).

    Sessions sit at all three levels on purpose, so ancestor-or-self is
    exercised: T's own session, G's and P's all reach the single leaf group.
    """
    groups = (
        Group(
            id="P", promotion="PR1", parent_group=None, level=GroupLevel.PROMO, label="P", size=30
        ),
        Group(id="G", promotion="PR1", parent_group="P", level=GroupLevel.TD, label="G", size=30),
        Group(id="T", promotion="PR1", parent_group="G", level=GroupLevel.TP, label="T", size=15),
    )
    sessions = (
        tiny_session("s_leaf", "T", "T1", "C1"),
        tiny_session("s_mid", "G", "T1", "C1"),
        tiny_session("s_top", "P", "T2", "C2"),
    )
    rooms = (
        Room(id="R1", building="B", code="R1", capacity=30, type=RoomType.SALLE),
        Room(id="R2", building="B", code="R2", capacity=30, type=RoomType.SALLE),
    )
    return Instance(
        programmes=(Programme(id="PG", code="PG", label="PG", degree_cycle="L", department="D"),),
        promotions=(
            Promotion(
                id="PR1", programme="PG", level="L1", academic_year="2025-2026", student_count=30
            ),
        ),
        groups=groups,
        teachers=(
            Teacher(id="T1", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18),
            Teacher(id="T2", department="D", rank=TeacherRank.ASSISTANT, max_hours_per_week=18),
        ),
        courses=(
            Course(
                id="C1",
                code="C1",
                department="D",
                programme="PG",
                level="L1",
                semester=2,
                credits=3,
            ),
            Course(
                id="C2",
                code="C2",
                department="D",
                programme="PG",
                level="L1",
                semester=2,
                credits=3,
            ),
        ),
        sessions=sessions,
        rooms=rooms,
        slots=tiny_slots(),
        availability=(),
        holidays=(),
        calendar_config={"periods_per_day": "5", "days_per_week": "2"},
        constraints=(
            ConstraintDefinition(
                code="S2",
                name="idle",
                kind=ConstraintKind.SOFT,
                default_weight=0.25,
                xhstt_reference=None,
            ),
        ),
    )
