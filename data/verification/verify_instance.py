"""Verify the reference instance against the figures the documentation states.

The three specification documents state the instance's content and its five
verification results as FACTS. This script checks that the files in
data/instance/ actually match them. If it fails, either the instance changed or
the documentation is now false — both need fixing, neither should be ignored.

Standalone by design: no dependency on the backend, no third-party package. The
13 CSVs are the contract between the generator and the application, so the
checker that guards that contract must not depend on either side of it.

    python data/verification/verify_instance.py

Exits 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import collections
import csv
import pathlib
import sys

INSTANCE = pathlib.Path(__file__).resolve().parents[1] / "instance"

failures: list[str] = []
notes: list[str] = []


def load(name: str) -> list[dict[str, str]]:
    with open(INSTANCE / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def check(label: str, got: object, expected: object) -> None:
    ok = str(got) == str(expected)
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<46} {got}")
    if not ok:
        failures.append(f"{label}: got {got}, documented {expected}")


def truthy(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes"}


sessions = load("sessions.csv")
rooms = load("rooms.csv")
slots = load("slots.csv")
groups = load("groups.csv")
teachers = load("teachers.csv")
availability = load("teacher_availability.csv")
holidays = load("holidays.csv")
students = load("students.csv")
catalogue = load("constraint_catalogue.csv")

group_size = {g["group_id"]: int(g["n_students"]) for g in groups}
open_slots = sum(1 for s in slots if truthy(s["is_open"]))


def demand(session: dict[str, str]) -> int:
    """Periods this session consumes in a week."""
    return int(session["duration_periods"]) * int(session.get("occurrences_per_week", 1))


# ── Content (Cahier des Charges, Table 10) ─────────────────────────────
print("\nContent of the instance")
by_type = collections.Counter(s["session_type"] for s in sessions)
check("sessions CM / TD / TP", f"{by_type['CM']} / {by_type['TD']} / {by_type['TP']}", "32 / 82 / 104")
by_dur = collections.Counter(s["duration_periods"] for s in sessions)
check("durations 1-period / 2-period", f"{by_dur['1']} / {by_dur['2']}", "114 / 104")
by_grp = collections.Counter(g["group_type"] for g in groups)
check(
    "groups PROMO / TD / TP",
    f"{by_grp['PROMO']} / {by_grp['TD']} / {by_grp['TP']}",
    "6 / 15 / 30",
)
by_room = collections.Counter(r["room_type"] for r in rooms)
check(
    "rooms Amphi / Salle / Lab_Info / Lab_Sciences",
    f"{by_room['Amphi']} / {by_room['Salle']} / {by_room['Lab_Info']} / {by_room['Lab_Sciences']}",
    "2 / 7 / 8 / 3",
)
check("students", len(students), 425)
check("teachers", len(teachers), 44)
check("open slots of total", f"{open_slots} / {len(slots)}", "28 / 30")
check("holidays, of which lunar", f"{len(holidays)}, {sum(1 for h in holidays if truthy(h['is_islamic']))}", "18, 10")
check("availability rows", len(availability), 157)
check("teachers with a declaration", len({a["teacher_id"] for a in availability}), 41)

# Every generated declaration must be distinguishable from a real one.
foreign = {a["source"] for a in availability} - {"SYNTHETIC"}
check("availability rows all marked SYNTHETIC", not foreign, True)

# ── Constraint catalogue ───────────────────────────────────────────────
print("\nConstraint catalogue")
kinds = collections.Counter(c["kind"] for c in catalogue)
check("hard / soft", f"{kinds['HARD']} / {kinds['SOFT']}", "12 / 7")
soft = sorted(
    (c["code"] for c in catalogue if c["kind"] == "SOFT"),
    key=lambda c: int(c[1:]),
)
check("soft codes", ",".join(soft), "S2,S3,S4,S5,S6,S7,S10")
check(
    "soft default weights sum",
    round(sum(float(c["default_weight"]) for c in catalogue if c["kind"] == "SOFT"), 4),
    0.9,
)
# S1, S8 and S9 were retired during specification revision. Codes are permanent
# identifiers used in the catalogue, the conflict report and weight_delta
# parameters — reusing one would silently change the meaning of stored data.
check("retired codes S1/S8/S9 absent", not ({"S1", "S8", "S9"} & set(soft)), True)

# ── The five verifications (Cahier des Charges, Table 11) ──────────────
print("\nThe five verifications")

# 1 — every session can find a room of the required type and sufficient capacity
unplaceable = [
    s
    for s in sessions
    if not any(
        r["room_type"] == s["required_room_type"] and int(r["capacity"]) >= group_size.get(s["group_id"], 0)
        for r in rooms
    )
]
check("1. sessions without a suitable room", len(unplaceable), 0)

# 2 — open slots cover the demand for each room type
#
# TWO bounds, not one. Counting periods is necessary but NOT sufficient, and
# relying on it alone hid a genuinely infeasible instance for three sessions of
# debugging — the solver returned UNKNOWN rather than INFEASIBLE, and the
# missing capacity was read as a search-performance problem.
#
# A multi-period session needs its periods CONSECUTIVE and inside ONE day: H8
# forbids crossing a day boundary and H9 forbids closed slots. So the open
# slots of a week are not a flat pool of periods but a set of maximal
# contiguous runs, and a run of length L offers a room only floor(L / d)
# disjoint windows for sessions of duration d — whatever the period count
# says. With five-period days and two-period laboratory sessions, one period
# per room-day is structurally unusable: 20% of the apparent capacity does not
# exist. Each 2-period session occupies a disjoint d-window inside some run, so
# this bound holds no matter what else shares the run.
open_by_day: dict[str, list[int]] = collections.defaultdict(list)
for s in slots:
    if truthy(s["is_open"]):
        open_by_day[s["day_index"]].append(int(s["slot_id"]))

runs: list[int] = []
for day_slots in open_by_day.values():
    length, previous = 0, None
    for idx in sorted(day_slots):
        if previous is not None and idx == previous + 1:
            length += 1
        else:
            if length:
                runs.append(length)
            length = 1
        previous = idx
    if length:
        runs.append(length)


def windows(d: int) -> int:
    """Disjoint d-period windows one room offers across the week."""
    return sum(length // d for length in runs)


print("     2. occupancy per room type")
for room_type in sorted({r["room_type"] for r in rooms}):
    n_rooms = sum(1 for r in rooms if r["room_type"] == room_type)
    capacity = n_rooms * open_slots
    required = sum(demand(s) for s in sessions if s["required_room_type"] == room_type)
    pct = 100 * required / capacity
    flag = "  <-- tightest point of the instance" if pct > 90 else ""
    print(f"           {room_type:<14} {required:>4} / {capacity:<4} = {pct:5.1f}%{flag}")
    if pct > 100:
        failures.append(f"room type {room_type} is over-subscribed at {pct:.1f}%")
    elif pct > 90:
        notes.append(
            f"{room_type} at {pct:.1f}% — withdrawing one room very probably makes the instance "
            f"infeasible. At this saturation a modelling regression looks like INFEASIBLE."
        )

    # The contiguity bound, per duration. This is the one that actually binds.
    durations = collections.Counter(
        int(s["duration_periods"])
        for s in sessions
        if s["required_room_type"] == room_type
        for _ in range(int(s.get("occurrences_per_week", 1)))
    )
    for d, count in sorted(durations.items()):
        if d < 2:
            continue
        seats = n_rooms * windows(d)
        share = 100 * count / seats if seats else float("inf")
        print(
            f"             {d}-period windows {count:>4} / {seats:<4} = {share:5.1f}%"
            f"{'  <-- OVER-SUBSCRIBED' if count > seats else ''}"
        )
        if count > seats:
            failures.append(
                f"room type {room_type}: {count} sessions of {d} periods but only {seats} "
                f"disjoint {d}-period windows ({n_rooms} rooms x {windows(d)} per room). "
                f"Short by {count - seats}. The instance has NO solution — this is a "
                f"pigeonhole argument, not a solver-performance question."
            )
        elif share > 90:
            notes.append(
                f"{room_type}: {d}-period windows at {share:.1f}% — the binding constraint "
                f"on this type, tighter than its {pct:.1f}% period occupancy suggests."
            )

# 3 — no teacher exceeds the maximum load of their rank
max_hours = {t["teacher_id"]: int(t["max_hours_per_week"]) for t in teachers}
load: collections.Counter[str] = collections.Counter()
for s in sessions:
    load[s["teacher_id"]] += demand(s)
period_hours = 1.5  # 90-minute periods
over = [t for t, periods in load.items() if periods * period_hours > max_hours.get(t, 0)]
check("3. teachers above their rank limit", len(over), 0)
heaviest = max(load.values())
check("   heaviest load, periods / hours", f"{heaviest} / {heaviest * period_hours:g}", "12 / 18")

# 4 — each teacher keeps enough free slots for the sessions assigned
unavailable = collections.Counter(
    a["teacher_id"] for a in availability if not truthy(a["is_available"])
)
margins = {t: (open_slots - unavailable.get(t, 0)) - load.get(t, 0) for t in max_hours}
check("4. teachers in difficulty", sum(1 for m in margins.values() if m < 0), 0)
check("   smallest margin, free slots", min(margins.values()), 11)

# 5 — the group hierarchy is consistent
ids = {g["group_id"] for g in groups}
dangling = [g for g in groups if g["parent_group_id"] and g["parent_group_id"] not in ids]
check("5. invalid parent references", len(dangling), 0)
declared = {g["group_id"]: int(g["n_students"]) for g in groups if g["group_type"] == "TP"}
actual = collections.Counter(s["tp_group_id"] for s in students)
check(
    "   TP subgroups whose size mismatches",
    sum(1 for g, n in declared.items() if actual.get(g, 0) != n),
    0,
)

# ── Known gaps, reported but not failed ────────────────────────────────
if not any(truthy(a["is_available"]) for a in availability):
    notes.append(
        "No availability row is positive and there is no 'preferred' state in the schema, "
        "yet S5 'Teacher preference' carries weight 0.20 — the second highest. S5 therefore "
        "measures a labelled proxy (sessions placed in the first or last period of the day), "
        "not what any teacher asked for, and the availability grid offers two states because "
        "there is no third to record. Both are deliberate and recorded — C-12 in "
        "docs/open-questions.md — not defects to fix here."
    )

print()
for note in notes:
    print(f"  NOTE  {note}")

if failures:
    print(f"\n{len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  - {f}")
    print("\nEither the instance changed or the documentation is now false. Fix both.")
    sys.exit(1)

print("\nAll checks passed. The instance matches its documentation.")
