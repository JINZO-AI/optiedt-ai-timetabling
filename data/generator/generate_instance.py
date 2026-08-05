"""Generate the reference instance — the PPM §10 deliverable.

    python data/generator/generate_instance.py --out some/directory

**Why this exists.** ADR-008 decided the application runs on a generated
instance rather than on merged public data, on the condition that the data "is
not invented at random and is verified before use". The 13 CSVs in
`data/instance/` were produced without a committed generator, so the condition
was met by the *verification* and not by the *generation* — and PPM §10 lists
the generator as a deliverable. This is that deliverable.

⚠️ **It does not reproduce `data/instance/` byte for byte, and it is important
to say so rather than imply otherwise.** The committed files carry 425 student
names, 44 teacher names and one particular teacher-to-session assignment drawn
from a random stream that was never committed. That stream is not recoverable,
so a generator emitting those exact rows would be a copy wearing a generator's
name. What it reproduces is **every figure the documentation states as a fact**
— which is precisely the binding ADR-008 creates, since the documents state the
instance's content and its five verification results and would become false if
those changed.

**The contract this must satisfy** is `data/verification/verify_instance.py`,
which reads the 13 CSVs and nothing else. Run it against this generator's
output:

    python data/generator/generate_instance.py --out /tmp/generated
    python data/verification/verify_instance.py --instance /tmp/generated

⚠️ **Imports nothing from `backend/`, by design.** The 13 CSVs *are* the
contract between the generator and the application (docs/data-and-instance.md),
so neither side may depend on the other — the same reasoning that keeps
`verify_instance.py` standalone. Standard library only.

⚠️ **The room mix is the post-C-13 one: Amphi 2 · Salle 7 · Lab_Info 8 ·
Lab_Sciences 3.** ADR-008 as first written quoted the PDFs' superseded figures,
and a generator reproducing those literally would emit an instance with **no
solution**: every laboratory session spans two periods, a two-period session
must fit inside one day, and a five-period day gives a room only two such
windows — so six computer laboratories offer 66 windows against 80 needed.
Read the correction in ADR-008 before changing any room count.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

# ── The shape of the faculty ───────────────────────────────────────────
#
# Every count below is one the documentation states as a fact. Changing one
# means changing the documentation and re-running verify_instance.py, which is
# exactly the coupling ADR-008 describes.

ACADEMIC_YEAR = "2025-2026"
SEMESTER = "S2"

PROGRAMMES = [
    # code, label, degree cycle, department
    ("INFO", "Licence Informatique", "L", "Informatique"),
    ("MATH", "Licence Mathematiques", "L", "Mathematiques"),
    ("MINFO", "Master Informatique", "M", "Informatique"),
]

#: programme index (1-based), level, students, TD groups, courses, courses with TP
PROMOTIONS = [
    (1, "L1", 120, 4, 6, 4),
    (1, "L2", 90, 3, 6, 4),
    (1, "L3", 70, 2, 5, 3),
    (2, "L1", 60, 2, 5, 3),
    (2, "L2", 45, 2, 5, 3),
    (3, "M1", 40, 2, 5, 3),
]

#: Laboratory type per programme. MATH practicals sit in science laboratories,
#: everything else in computer laboratories - which is what makes Lab_Info the
#: binding resource at 90.9 % of its two-period windows.
LAB_BY_PROGRAMME = {1: "Lab_Info", 2: "Lab_Sciences", 3: "Lab_Info"}

#: Credits cycle deterministically over the courses of the faculty so the
#: documented spread (14 x 5, 8 x 4, 10 x 3) comes out.
CREDIT_CYCLE = [5, 5, 3, 4, 4, 5, 5, 5, 3, 3, 4, 4, 3, 5, 5, 3, 4, 5, 3, 3, 5, 5, 5, 4, 5, 4, 3, 4, 3, 3, 5, 5]

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
PERIODS = [
    ("P1", "08:30", "10:00"),
    ("P2", "10:10", "11:40"),
    ("P3", "11:50", "13:20"),
    ("P4", "14:00", "15:30"),
    ("P5", "15:40", "17:10"),
]
#: Saturday afternoon is closed. ⚠️ This is CONFIGURATION, never a constraint
#: (ADR-003, invariant 7) - it sets is_open = 0 and H9 does the rest.
CLOSED = {(5, 3), (5, 4)}

ROOMS = [
    # building, code, capacity, type
    ("Bloc A", "Amphi A", 250, "Amphi"),
    ("Bloc A", "Amphi B", 150, "Amphi"),
    ("Bloc B", "LabInfo7", 20, "Lab_Info"),
    ("Bloc B", "S02", 30, "Salle"),
    ("Bloc B", "S03", 40, "Salle"),
    ("Bloc B", "S04", 35, "Salle"),
    ("Bloc B", "S05", 35, "Salle"),
    ("Bloc B", "S06", 35, "Salle"),
    ("Bloc B", "S07", 30, "Salle"),
    ("Bloc B", "LabInfo8", 20, "Lab_Info"),
    ("Bloc B", "S09", 45, "Salle"),
    ("Bloc B", "LabSci3", 24, "Lab_Sciences"),
    ("Bloc C", "LabInfo1", 20, "Lab_Info"),
    ("Bloc C", "LabInfo2", 20, "Lab_Info"),
    ("Bloc C", "LabInfo3", 20, "Lab_Info"),
    ("Bloc C", "LabInfo4", 20, "Lab_Info"),
    ("Bloc C", "LabInfo5", 20, "Lab_Info"),
    ("Bloc C", "LabInfo6", 20, "Lab_Info"),
    ("Bloc C", "LabSci1", 24, "Lab_Sciences"),
    ("Bloc C", "LabSci2", 24, "Lab_Sciences"),
]

#: rank, count, maximum hours a week. Periods are 90 minutes, so the period cap
#: is max_hours / 1.5 - which is what verification 3 checks against.
RANKS = [
    ("Professeur", 7, 9),
    ("Maitre de Conferences", 11, 12),
    ("Maitre Assistant", 13, 18),
    ("Assistant", 13, 24),
]

HOLIDAYS = [
    ("2025-10-15", "Fete de l'Evacuation", 0, 0),
    ("2025-12-17", "Fete de la Revolution et de la Jeunesse", 0, 0),
    ("2026-01-01", "Jour de l'An", 0, 0),
    ("2026-01-14", "Fete de la Revolution", 0, 0),
    ("2026-03-20", "Fete de l'Independance", 0, 0),
    ("2026-04-09", "Journee des Martyrs", 0, 0),
    ("2026-05-01", "Fete du Travail", 0, 0),
    ("2026-07-25", "Fete de la Republique", 0, 0),
    ("2026-06-27", "Ras el Am el Hejri", 1, 1),
    ("2026-09-04", "Mouled", 1, 1),
    ("2026-02-17", "Nuit du Doute", 1, 1),
    ("2026-03-19", "Aid el Fitr (1)", 1, 1),
    ("2026-03-20", "Aid el Fitr (2)", 1, 1),
    ("2026-03-21", "Aid el Fitr (3)", 1, 1),
    ("2026-05-27", "Aid el Idha (1)", 1, 1),
    ("2026-05-28", "Aid el Idha (2)", 1, 1),
    ("2026-05-29", "Aid el Idha (3)", 1, 1),
    ("2026-06-15", "Achoura", 1, 1),
]

CATALOGUE = [
    ("H1", "No teacher overlap", "HARD", "", "AvoidClashesConstraint", "A teacher has <=1 session per slot"),
    ("H2", "No group overlap", "HARD", "", "AvoidClashesConstraint", "A group has <=1 session per slot"),
    ("H3", "No room overlap", "HARD", "", "AvoidClashesConstraint", "A room hosts <=1 session per slot"),
    ("H4", "Room type respected", "HARD", "", "PreferResourcesConstraint", "A session uses a room of its required type"),
    ("H5", "Room capacity", "HARD", "", "PreferResourcesConstraint", "A room seats the whole group"),
    ("H6", "Teacher qualification", "HARD", "", "PreferResourcesConstraint", "A session is given by its declared teacher"),
    ("H7", "Teacher availability", "HARD", "", "AvoidUnavailableTimesConstraint", "No session in a slot a teacher declared unavailable"),
    ("H8", "Session inside one day", "HARD", "", "SplitEventsConstraint", "A multi-period session does not cross a day boundary"),
    ("H9", "Closed slots and holidays", "HARD", "", "AvoidUnavailableTimesConstraint", "No session in a closed slot"),
    ("H10", "Locked sessions", "HARD", "", "AssignTimeConstraint", "A locked session keeps its slot and room"),
    ("H11", "One room per session", "HARD", "", "AssignResourceConstraint", "A session occupies exactly one room"),
    ("H12", "Group hierarchy", "HARD", "", "AvoidClashesConstraint", "Parent busy => children busy (and vice-versa)"),
    ("S2", "Student idle time", "SOFT", "0.25", "LimitIdleTimesConstraint", "Gaps in a group's day"),
    ("S3", "Teacher idle time", "SOFT", "0.15", "LimitIdleTimesConstraint", "Gaps in a teacher's day"),
    ("S4", "Extra working day", "SOFT", "0.10", "ClusterBusyTimesConstraint", "A teacher spread over more days than needed"),
    ("S5", "Teacher preference", "SOFT", "0.20", "", "Sessions in a period a teacher would rather avoid"),
    ("S6", "Room efficiency", "SOFT", "0.10", "", "Rooms used far from their type's average"),
    ("S7", "Subject spread", "SOFT", "0.10", "SpreadEventsConstraint", "One course reaching a group twice in a day"),
    ("S10", "Lunch break", "SOFT", "0.0", "", "A group occupying the period that straddles noon"),
]

FIRST_NAMES = [
    "Amine", "Sonia", "Karim", "Ines", "Mehdi", "Rania", "Youssef", "Leila", "Nizar", "Emna",
    "Hatem", "Sarra", "Bilel", "Nadia", "Slim", "Olfa", "Wassim", "Hela", "Anis", "Dorra",
    "Marwen", "Ahlem", "Skander", "Amira", "Tarek", "Sabrine", "Zied", "Mouna", "Kais", "Rim",
    "Nabil", "Asma", "Fares", "Sana", "Chokri", "Ilhem", "Riadh", "Nesrine", "Hamza", "Yosra",
    "Aymen", "Meriem", "Sofiene", "Khaoula",
]

LAST_NAMES = [
    "Ben Salah", "Trabelsi", "Gharbi", "Ferchichi", "Bouazizi", "Jelassi", "Khelifi", "Mansour",
    "Naifar", "Saidi", "Chaabane", "Hammami", "Bouzid", "Mejri", "Sassi", "Ayari", "Dridi",
    "Zouari", "Belhaj", "Kacem", "Rekik", "Ghanmi", "Barhoumi", "Jaziri", "Ouali", "Tlili",
    "Marzouki", "Guesmi", "Hadj Ali", "Sellami", "Karoui", "Ben Amor", "Riahi", "Chebbi",
    "Baccouche", "Mnasri", "Hentati", "Abdelli", "Fakhfakh", "Louati", "Nasri", "Cherif",
    "Jarraya", "Bahri",
]

PERIOD_HOURS = 1.5


def build() -> dict[str, tuple[list[str], list[list[object]]]]:
    """Every table, as (header, rows). Deterministic: no randomness at all.

    ⚠️ Names are drawn from fixed pools by index rather than by a random
    generator. A seeded shuffle would be reproducible too, but only for as long
    as nobody upgrades Python - `random`'s stream is not a stable API across
    versions, and a deliverable whose output changes with the interpreter is
    not a deliverable.
    """
    tables: dict[str, tuple[list[str], list[list[object]]]] = {}

    # ── programmes ─────────────────────────────────────────────────────
    tables["programmes.csv"] = (
        ["programme_id", "code", "label", "degree_cycle", "department"],
        [[i + 1, code, label, cycle, dept] for i, (code, label, cycle, dept) in enumerate(PROGRAMMES)],
    )

    # ── promotions ─────────────────────────────────────────────────────
    promo_rows = []
    for i, (prog, level, students, _tds, _courses, _with_tp) in enumerate(PROMOTIONS):
        promo_rows.append([i + 1, prog, level, ACADEMIC_YEAR, students])
    tables["promotions.csv"] = (
        ["promotion_id", "programme_id", "level", "academic_year", "n_students"],
        promo_rows,
    )

    # ── groups: one PROMO, n TD, 2n TP ─────────────────────────────────
    #
    # Sizes are split so they SUM to the promotion exactly - verification 5
    # compares the declared TP size against the students actually enrolled in
    # it, so an approximate split fails rather than rounds.
    group_rows: list[list[object]] = []
    td_groups: dict[int, list[int]] = {}
    tp_groups: dict[int, list[int]] = {}
    gid = 0
    for pindex, (prog, level, students, n_td, _courses, _with_tp) in enumerate(PROMOTIONS, start=1):
        code = PROGRAMMES[prog - 1][0]
        gid += 1
        promo_gid = gid
        group_rows.append([gid, pindex, "", "PROMO", f"{code}-{level}", students])
        td_groups[pindex] = []
        tp_groups[pindex] = []
        for t in range(n_td):
            size = students // n_td + (1 if t < students % n_td else 0)
            gid += 1
            td_gid = gid
            td_groups[pindex].append(td_gid)
            group_rows.append([gid, pindex, promo_gid, "TD", f"{code}-{level}-G{t + 1}", size])
            for p in range(2):
                sub = size // 2 + (1 if p < size % 2 else 0)
                gid += 1
                tp_groups[pindex].append(gid)
                group_rows.append(
                    [gid, pindex, td_gid, "TP", f"{code}-{level}-G{t + 1}.{p + 1}", sub]
                )
    tables["groups.csv"] = (
        ["group_id", "promotion_id", "parent_group_id", "group_type", "label", "n_students"],
        group_rows,
    )
    group_size = {int(r[0]): int(r[5]) for r in group_rows}

    # ── courses ────────────────────────────────────────────────────────
    course_rows: list[list[object]] = []
    courses_of_promo: dict[int, list[int]] = {}
    cid = 0
    for pindex, (prog, level, _students, _n_td, n_courses, _with_tp) in enumerate(PROMOTIONS, start=1):
        code = PROGRAMMES[prog - 1][0]
        dept = PROGRAMMES[prog - 1][3]
        courses_of_promo[pindex] = []
        for n in range(n_courses):
            cid += 1
            courses_of_promo[pindex].append(cid)
            course_rows.append(
                [
                    cid,
                    f"{code}{level}-{n + 1:02d}",
                    f"Matiere {n + 1} {level}",
                    dept,
                    prog,
                    level,
                    SEMESTER,
                    CREDIT_CYCLE[(cid - 1) % len(CREDIT_CYCLE)],
                ]
            )
    tables["courses.csv"] = (
        ["course_id", "code", "title", "department", "programme_id", "level", "semester", "credits"],
        course_rows,
    )

    # ── teachers ───────────────────────────────────────────────────────
    teacher_rows: list[list[object]] = []
    rank_of: dict[str, str] = {}
    cap_periods: dict[str, int] = {}
    tid = 0
    for rank, count, max_hours in RANKS:
        for _ in range(count):
            tid += 1
            key = f"T{tid:03d}"
            first = FIRST_NAMES[(tid - 1) % len(FIRST_NAMES)]
            last = LAST_NAMES[(tid - 1) % len(LAST_NAMES)]
            # Informatique and Mathematiques alternate so both departments are
            # represented at every rank.
            dept = "Informatique" if tid % 2 == 0 else "Mathematiques"
            email = f"{first.lower()}.{last.split()[-1].lower()}@fac.tn"
            teacher_rows.append([key, first, last, dept, rank, max_hours, email])
            rank_of[key] = rank
            cap_periods[key] = int(max_hours / PERIOD_HOURS)
    tables["teachers.csv"] = (
        ["teacher_id", "first_name", "last_name", "department", "rank", "max_hours_per_week", "email"],
        teacher_rows,
    )

    lecturers = [r[0] for r in teacher_rows if rank_of[r[0]] in {"Professeur", "Maitre de Conferences"}]
    tutors = [r[0] for r in teacher_rows if rank_of[r[0]] in {"Maitre Assistant", "Assistant"}]

    # ⚠️ Every TD/TP teacher is capped at 12 periods, not at their rank's own
    # limit. Verification 3 checks BOTH that nobody exceeds their rank and that
    # the heaviest load is exactly 12 periods (18 h) - so an Assistant, whose
    # rank allows 16, must still stop at 12 or the second figure moves.
    HEAVIEST = 12
    load: dict[str, int] = {t[0]: 0 for t in teacher_rows}

    def assign(pool: list[str], periods: int) -> str:
        """The least-loaded eligible teacher; ties by id, so it is total."""
        best = min(
            (t for t in pool if load[t] + periods <= min(cap_periods[t], HEAVIEST)),
            key=lambda t: (load[t], t),
            default=None,
        )
        if best is None:  # pragma: no cover - would mean the shape changed
            raise SystemExit("no teacher can take another session: the shape above is inconsistent")
        load[best] += periods
        return best

    # ── sessions ───────────────────────────────────────────────────────
    session_rows: list[list[object]] = []
    sid = 0
    promo_gid_of = {}
    running = 0
    for pindex, (_prog, _level, _students, n_td, _courses, _with_tp) in enumerate(PROMOTIONS, start=1):
        promo_gid_of[pindex] = running + 1
        running += 1 + n_td * 3

    for pindex, (prog, _level, _students, _n_td, _n_courses, with_tp) in enumerate(PROMOTIONS, start=1):
        lab = LAB_BY_PROGRAMME[prog]
        for order, course in enumerate(courses_of_promo[pindex]):
            sid += 1
            session_rows.append(
                [f"S{sid:04d}", course, promo_gid_of[pindex], assign(lecturers, 1), "CM", 1, 1, "Amphi", 0]
            )
            for td in td_groups[pindex]:
                sid += 1
                session_rows.append(
                    [f"S{sid:04d}", course, td, assign(tutors, 1), "TD", 1, 1, "Salle", 0]
                )
            if order < with_tp:
                for tp in tp_groups[pindex]:
                    sid += 1
                    session_rows.append(
                        [f"S{sid:04d}", course, tp, assign(tutors, 2), "TP", 2, 1, lab, 0]
                    )
    tables["sessions.csv"] = (
        [
            "session_id", "course_id", "group_id", "teacher_id", "session_type",
            "duration_periods", "occurrences_per_week", "required_room_type", "is_locked",
        ],
        session_rows,
    )

    # ── rooms ──────────────────────────────────────────────────────────
    tables["rooms.csv"] = (
        ["room_id", "building", "code", "capacity", "room_type", "has_projector", "has_computers"],
        [
            [i + 1, building, code, cap, kind, 1, 1 if kind == "Lab_Info" else 0]
            for i, (building, code, cap, kind) in enumerate(ROOMS)
        ],
    )

    # ── slots ──────────────────────────────────────────────────────────
    slot_rows: list[list[object]] = []
    for d, day in enumerate(DAYS):
        for p, (label, start, end) in enumerate(PERIODS):
            slot_rows.append(
                [d * len(PERIODS) + p, d, day, p, label, start, end, 0 if (d, p) in CLOSED else 1]
            )
    tables["slots.csv"] = (
        ["slot_id", "day_index", "day_name", "period_index", "period_label", "start_time", "end_time", "is_open"],
        slot_rows,
    )
    open_slots = [int(r[0]) for r in slot_rows if r[7] == 1]

    # ── students ───────────────────────────────────────────────────────
    #
    # Enrolled to fill each TP group to its DECLARED size exactly: verification
    # 5 compares the two and a near-enough split fails.
    student_rows: list[list[object]] = []
    n = 0
    for pindex, _ in enumerate(PROMOTIONS, start=1):
        for tp in tp_groups[pindex]:
            parent = next(int(r[2]) for r in group_rows if int(r[0]) == tp)
            for _ in range(group_size[tp]):
                n += 1
                student_rows.append(
                    [
                        f"E{n:05d}",
                        FIRST_NAMES[(n * 7) % len(FIRST_NAMES)],
                        LAST_NAMES[(n * 13) % len(LAST_NAMES)],
                        pindex,
                        parent,
                        tp,
                    ]
                )
    tables["students.csv"] = (
        ["student_id", "first_name", "last_name", "promotion_id", "td_group_id", "tp_group_id"],
        student_rows,
    )

    # ── teacher availability ───────────────────────────────────────────
    #
    # 157 declarations over 41 of the 44 teachers, every one an UNAVAILABILITY
    # and every one marked SYNTHETIC so a generated declaration is
    # distinguishable from a real one at any moment (ADR-008's honesty marker).
    #
    # ⚠️ The counts are chosen to land verification 4 exactly. Its margin is
    # (open slots - declarations) - assigned periods, it must be >= 0 for every
    # teacher, and the SMALLEST must be 11. So one teacher already at the
    # heaviest load of 12 periods declares 5 slots - 28 - 5 - 12 = 11 - and
    # nobody else is allowed to go lower.
    TOTAL_DECLARATIONS = 157
    DECLARING = 41
    SMALLEST_MARGIN = 11

    declaring = [r[0] for r in teacher_rows][:DECLARING]
    binding = next((t for t in declaring if load[t] == HEAVIEST), declaring[0])
    counts: dict[str, int] = {binding: len(open_slots) - SMALLEST_MARGIN - load[binding]}

    remaining = TOTAL_DECLARATIONS - counts[binding]
    others = [t for t in declaring if t != binding]
    base, extra = divmod(remaining, len(others))
    for i, t in enumerate(others):
        counts[t] = base + (1 if i < extra else 0)

    availability_rows: list[list[object]] = []
    aid = 0
    for index, teacher in enumerate(declaring):
        # A deterministic stride, offset per teacher, so declarations are
        # spread across the week rather than piled onto one day - a teacher
        # unavailable for a whole day makes H7 far harder than the count says.
        stride = 3 + (index % 4)
        chosen = sorted({open_slots[(index * 5 + k * stride) % len(open_slots)] for k in range(counts[teacher] * 3)})
        for slot in chosen[: counts[teacher]]:
            aid += 1
            availability_rows.append([aid, teacher, slot, 0, SEMESTER, ACADEMIC_YEAR, "SYNTHETIC"])
    tables["teacher_availability.csv"] = (
        ["availability_id", "teacher_id", "slot_id", "is_available", "semester", "academic_year", "source"],
        availability_rows,
    )

    # ── holidays ───────────────────────────────────────────────────────
    tables["holidays.csv"] = (
        ["holiday_id", "holiday_date", "label", "is_islamic", "is_approximate", "blocks_scheduling"],
        [[i + 1, date, label, islamic, approx, 1] for i, (date, label, islamic, approx) in enumerate(HOLIDAYS)],
    )

    # ── calendar configuration ─────────────────────────────────────────
    #
    # ⚠️ Every row here is CONFIGURATION acting through mechanisms the model
    # already contains (ADR-003). A closed half-day sets is_open = 0 and H9
    # removes those slots; a shortened-day window shifts DISPLAYED hours only,
    # leaving the slot index untouched. Adding a CP-SAT constraint for Ramadan
    # or a closed Saturday is a bug, not a feature.
    tables["calendar_config.csv"] = (
        ["key", "value"],
        [
            ["periods_per_day", len(PERIODS)],
            ["days_per_week", len(DAYS)],
            ["slot_formula", "t = day_index*periods_per_day + period_index"],
            ["friday_afternoon_closed", "false"],
            ["saturday_afternoon_closed", "true"],
            ["academic_year", ACADEMIC_YEAR],
            ["semester", SEMESTER],
            ["ramadan_start", "2026-02-18"],
            ["ramadan_end", "2026-03-19"],
            ["ramadan_shift_minutes", 60],
            ["period_minutes", 90],
        ],
    )

    # ── constraint catalogue ───────────────────────────────────────────
    #
    # ⚠️ S1, S8 and S9 are RETIRED and must never be reused. Codes are stable
    # identifiers in the catalogue, the conflict report and weight_delta
    # parameters, so reusing one silently changes the meaning of stored data.
    tables["constraint_catalogue.csv"] = (
        ["constraint_id", "code", "name", "kind", "default_weight", "xhstt_ref", "description"],
        [[i + 1, *row] for i, row in enumerate(CATALOGUE)],
    )

    return tables


def write(tables: dict[str, tuple[list[str], list[list[object]]]], out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, (header, rows) in tables.items():
        with open(out / name, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        required=True,
        help="directory to write the 13 CSVs into (created if absent)",
    )
    args = parser.parse_args(argv)

    if args.out.resolve() == (pathlib.Path(__file__).resolve().parents[1] / "instance"):
        print(
            "Refusing to overwrite data/instance/.\n\n"
            "That directory holds the instance every measurement in docs/ was taken\n"
            "against - scores, timings, occupancy figures, the S5 range. This generator\n"
            "reproduces the documented FIGURES, not the committed rows, so replacing it\n"
            "would invalidate those measurements without any of them failing. Write\n"
            "somewhere else and compare.",
            file=sys.stderr,
        )
        return 2

    tables = build()
    write(tables, args.out)
    print(f"Wrote {len(tables)} files to {args.out}")
    for name, (_header, rows) in sorted(tables.items()):
        print(f"  {name:<28} {len(rows):>4} rows")
    print("\nNow check it against the documentation:")
    print(f"  python data/verification/verify_instance.py --instance {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
