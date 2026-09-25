"""Random, valid timetabling instances for property tests.

Instances are small enough to solve in about a second but exercise every feature the model
has: closed and penalised slots, breaks between periods, two campuses with travel times,
room types, nested student groups, online activities, fixed occurrences, availability of
every kind and rules of every type.
"""

from __future__ import annotations

from typing import Any

from hypothesis import strategies as st

from optiedt.problem.model import Problem
from tests.snapshot_builder import SnapshotBuilder

PERIOD_TIMES = (
    ("08:30", "10:00"),
    ("10:10", "11:40"),
    ("11:50", "13:20"),
    ("14:40", "16:10"),
    ("16:20", "17:50"),
)
RESOURCE_RULES = (
    "max_periods_per_day",
    "max_consecutive_periods",
    "max_days_per_week",
    "break_in_window",
    "avoid_slots",
    "earliest_start",
    "latest_end",
    "campus_travel",
)
ACTIVITY_RULES = (
    "min_days_between",
    "not_overlapping",
    "same_start",
    "same_day",
    "different_days",
    "precedence",
    "consecutive",
)
SLOT_RULES = ("avoid_slots", "earliest_start", "latest_end")


@st.composite
def instances(draw: st.DrawFn, *, hard_rules: bool = True) -> Problem:
    n_days = draw(st.integers(2, 3))
    n_periods = draw(st.integers(3, 5))
    slots = [(d, p) for d in range(n_days) for p in range(n_periods)]

    def some_slots(most: int) -> list[tuple[int, int]]:
        return draw(st.lists(st.sampled_from(slots), max_size=most, unique=True))

    b = SnapshotBuilder(
        days=n_days,
        periods=PERIOD_TIMES[:n_periods],
        joins=tuple(draw(st.booleans()) for _ in range(n_periods)),
        closed=some_slots(2),
        penalties=draw(st.dictionaries(st.sampled_from(slots), st.integers(1, 3), max_size=3)),
    )
    campuses = ["MAIN"]
    if draw(st.booleans()):
        b.campus("NORTH")
        campuses.append("NORTH")
        b.travel("MAIN", "NORTH", draw(st.sampled_from([5, 30, 120])))
    rooms = [
        b.room(
            f"R{i}",
            draw(st.sampled_from([20, 40, 80])),
            draw(st.sampled_from(["CLASSROOM", "LAB"])),
            campus=draw(st.sampled_from(campuses)),
            unavailable=some_slots(2),
        )
        for i in range(draw(st.integers(2, 5)))
    ]
    instructors = [
        b.instructor(
            f"T{i}",
            unavailable=some_slots(2),
            undesirable=some_slots(2),
            preferred=some_slots(3),
        )
        for i in range(draw(st.integers(1, 4)))
    ]
    groups: list[str] = []
    for r in range(draw(st.integers(1, 2))):
        root = b.group(f"Y{r}", draw(st.sampled_from([30, 60])), unavailable=some_slots(1))
        groups.append(root)
        if draw(st.booleans()):
            groups += [b.group(f"Y{r}-G{k}", 30, root, "tut") for k in range(2)]
    activities = []
    for a in range(draw(st.integers(2, 7))):
        sessions = draw(st.integers(1, 3))
        fixed = None
        if draw(st.integers(0, 5)) == 0:
            day, period = draw(st.sampled_from(slots))
            fixed = [(1, day, period, draw(st.sampled_from([None, *rooms])))]
        activities.append(
            b.activity(
                f"C{a}",
                groups=draw(st.lists(st.sampled_from(groups), min_size=1, max_size=2, unique=True)),
                instructors=draw(st.lists(st.sampled_from(instructors), max_size=2, unique=True)),
                duration=draw(st.integers(1, 2)),
                sessions=sessions,
                room_type=draw(st.sampled_from(["CLASSROOM", "LAB", None])),
                seats=draw(st.sampled_from([None, 15])),
                online=draw(st.integers(0, 4)) == 0,
                different_days=draw(st.booleans()),
                preferred_rooms=draw(st.lists(st.sampled_from(rooms), max_size=1)),
                avoided_rooms=draw(st.lists(st.sampled_from(rooms), max_size=1)),
                unavailable=some_slots(2),
                fixed=fixed,
            )
        )

    for _ in range(draw(st.integers(0, 5))):
        kind = draw(st.sampled_from(RESOURCE_RULES + ACTIVITY_RULES))
        targets: dict[str, Any] = {}
        if kind in RESOURCE_RULES:
            targets["instructors"] = draw(
                st.lists(st.sampled_from(instructors), max_size=2, unique=True)
            )
            targets["groups"] = draw(st.lists(st.sampled_from(groups), max_size=1))
            if kind in SLOT_RULES and draw(st.booleans()):
                targets["activities"] = draw(
                    st.lists(st.sampled_from(activities), min_size=1, max_size=2, unique=True)
                )
            if not any(targets.values()):
                targets["instructors"] = [instructors[0]]
        elif kind in ("precedence", "consecutive"):
            targets["activities"] = draw(
                st.lists(st.sampled_from(activities), min_size=2, max_size=2, unique=True)
            )
            targets["ordered"] = True
        elif kind == "min_days_between":
            targets["activities"] = draw(
                st.lists(st.sampled_from(activities), min_size=1, max_size=2, unique=True)
            )
        else:
            targets["activities"] = draw(
                st.lists(st.sampled_from(activities), min_size=2, max_size=3, unique=True)
            )
        hard = hard_rules and draw(st.booleans())
        b.rule(
            kind,
            params=_params(draw, kind, n_days, n_periods, slots),
            enforcement="hard" if hard else "soft",
            tier=draw(st.integers(1, 3)),
            weight=draw(st.integers(1, 3)),
            **targets,
        )
    return b.problem()


def _params(
    draw: st.DrawFn, kind: str, n_days: int, n_periods: int, slots: list[tuple[int, int]]
) -> dict[str, Any]:
    if kind in ("max_periods_per_day", "max_consecutive_periods"):
        return {"limit": draw(st.integers(1, 3))}
    if kind == "max_days_per_week":
        return {"limit": draw(st.integers(1, n_days - 1))}
    if kind == "break_in_window":
        periods = sorted(
            draw(st.lists(st.integers(0, n_periods - 1), min_size=2, max_size=3, unique=True))
        )
        return {"periods": periods, "min_free": draw(st.integers(1, len(periods)))}
    if kind == "avoid_slots":
        chosen = draw(st.lists(st.sampled_from(slots), min_size=1, max_size=3, unique=True))
        return {"slots": [list(slot) for slot in chosen]}
    if kind == "earliest_start":
        return {"period": draw(st.integers(1, n_periods - 1))}
    if kind == "latest_end":
        return {"period": draw(st.integers(0, n_periods - 2))}
    if kind == "min_days_between":
        return {"days": draw(st.integers(1, 2))}
    return {}
