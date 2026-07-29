# Provenance and verification of the reference archives

**Verified 2026-07-29** by opening the files, not by reading their documentation.

That distinction is the methodology, not a formality — and it paid off here. The
Kaggle archive's own `note.txt` claims *"Clean CSVs with full entity
relationships."* **44% of its timeslot rows are invalid.** A dataset can describe
itself as complete and contain errors.

All archives are **gitignored**, **never loaded into the application database**,
and **never merged with each other** (ADR-008).

---

## What is held

| Archive | Contents | Size |
|---|---|---|
| `itc2007-cct-master/` | 21 `comp*.ctt` instances + 2 toy instances, a third-party solver, a validator, published results | 4.1 MB |
| `Kaggle University Exam Scheduling/` | 6 CSVs — classrooms, courses, instructors, schedule, students, timeslots | 1.2 MB |
| `XHSTT-2014/` | `XHSTT-2014.xml`, single file | 14.0 MB |

---

## ITC-2007, Track 3 (curriculum-based) — **usable, validation only**

**Counts verified:** 21 `comp*.ctt` instances present, matching the figure in
`docs/figures/data-strategy.excalidraw.png`.

⚠️ **This is a source repository that bundles the instances with a third-party
solver — it is not the competition archive itself.** It ships `src/`,
`validator/`, `configs/`, `benchmark.py`, published `results/` and a
`CMakeLists.txt`. Describe it that way in the report; presenting the folder as
the official archive would misstate its provenance.

Role: **validate the course engine against published results.** The bundled
`validator/` and `results/` are what make that comparison possible — that is the
value of holding this repository rather than the bare instances.

Not loaded into the database: no individual students (per-course counts only),
and no CM/TD/TP distinction.

---

## XHSTT-2014 — **usable, constraint catalogue only**

**Count verified:** `25` `<Instance Id=...>` elements in the XML, matching the
figure's "25 instances".

Cite it as **"25 instances in the version held"**, not as a general fact. The
counts announced for this archive vary between versions, which is why the
project's documentation cites the **catalogue of constraint types read
directly** rather than any number taken from a summary. The bundled `note.txt`
says "15+ constraint types" and lists 11 countries — treat both as the
publisher's summary, not as verified figures.

Role: **the list of constraint types**, transcribed into
`data/instance/constraint_catalogue.csv`. **No data import.** The instances
concern secondary schools and are written in a form heavy to read.

---

## Kaggle, University Exam Scheduling — ⚠️ **two files invalid**

The archive describes itself as clean. It is not. Measured:

| File | Rows | Finding |
|---|---|---|
| `timeslots.csv` | 100 | **44 rows (44%) have `end_time` ≤ `start_time`** — e.g. row 2, Friday 13:00→12:00 |
| `schedule.csv` | 9,082 | **2,380 of 2,853 room+slot pairs host more than one course (83%)** |
| | | **2,637 of 4,173 instructor+slot pairs place the instructor in more than one room (63%)** |
| `classrooms.csv` | — | Usable — id, building, room number, capacity, room type |
| `students.csv` | 3,000 | Usable as enrolments **only** — see the privacy note below |
| `courses.csv`, `instructors.csv` | — | Usable |

These are not rounding errors or edge cases. A file in which 83% of room-slot
pairs are double-booked cannot serve as a reference for anything — which is the
concrete reason **merging the sources was rejected**: it would have placed
conflicts inside the data meant to serve as reference (ADR-008).

**Keep: the room list and student enrolments. Drop: `schedule.csv` and
`timeslots.csv`.**

### ⚠️ Privacy — `students.csv` carries personal data

Columns: `student_id, first_name, last_name, email, phone_number, address,
program_name, year`. 3,000 rows of names, email addresses, phone numbers and
postal addresses.

The values appear synthetic (`example.com` addresses), but **the file is
personal-data-shaped and must be treated as such**. This gives ADR-008's "rooms
and enrolments only" a concrete second justification beyond data quality:

- The application records **no student name** — a student is represented by the
  group they belong to, outside the examination module.
- **No student name, no email address and no personal identifier may ever enter
  the assistant's context payload.** Data minimisation is a stated requirement.

If any part of this file is ever used, take `student_id` and course enrolment
and **nothing else**.

---

## ITC-2007, Track 1 (examinations) — **not present, not opened**

Identified for increment 2. **Not in this folder and not yet examined.** Its
verification belongs at the start of increment 2, and **no property of it is
assumed before then.**

---

## What none of them provides

The reason a generated instance exists at all (ADR-008):

- CM / TD / TP session types
- The promotion → tutorial group → laboratory subgroup hierarchy
- A Tunisian calendar, its lunar holidays, or a shortened-day period
- **Teacher-declared availability** — which is precisely what the application
  exists to collect

---

## Original location

Copied from `C:\Users\Jinzo\Documents\projet stage\dataset` on 2026-07-29. That
copy is now redundant and can be removed.
