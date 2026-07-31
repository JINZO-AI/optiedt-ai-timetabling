# Data and the reference instance

## The instance is present and verified

The three PDFs **state the instance's verification results as facts** — 0 sessions without a suitable
room, 95% laboratory occupancy, a heaviest load of 12 periods, a smallest margin of 11 free slots, 425
students matching declared group sizes.

**Those claims were re-measured on 2026-07-29 against the actual files, and every one matched.**
The instance lives in `data/instance/` — 13 CSVs, 36 KB, committed.

⚠️ **One of them matched and was still wrong — read this before trusting a verification.** The "95%
laboratory occupancy" figure was arithmetically correct and described an instance that **had no
solution**: it counted periods, and a two-period session needs two *consecutive* periods inside one
day. Measuring the quantity the specification named is not the same as measuring the quantity that
determines feasibility. The room mix was repaired on 2026-07-30 (`Salle` 10 → 7, `Lab_Info` 6 → 8,
`Lab_Sciences` 2 → 3, total still 20 rooms) and the check now applies both bounds — see "91% is the
number to watch" below, and C-13 in `docs/open-questions.md`.

```bash
scripts/verify-instance.ps1
```

Run it after any change to the instance or the generator. It checks content *and* the five
verifications. A failure means either the instance changed or the documentation is now false — both
need fixing, neither should be ignored.

This matters beyond tidiness: ADR-008 accepts generated data **on condition that it is verified**. The
condition is now met by measurement rather than by assertion.

The *generator* itself remains a stated deliverable (PPM §10) and does not exist. That is a
reproducibility task, not a blocker — **and it is scheduled**: item 9 of `docs/status.md`'s "Next, in
order", latest sensible point Phase 6. It must reproduce *the* documented instance, not merely a valid
one (ADR-008), because every measured figure in these documents is measured against that one.

## Schema — as the files actually are

| File | Rows | Columns |
|---|---|---|
| `programmes.csv` | 3 | `programme_id, code, label, degree_cycle, department` |
| `promotions.csv` | 6 | `promotion_id, programme_id, level, academic_year, n_students` |
| `groups.csv` | 51 | `group_id, promotion_id, parent_group_id, group_type, label, n_students` |
| `students.csv` | 425 | `student_id, first_name, last_name, promotion_id, td_group_id, tp_group_id` |
| `teachers.csv` | 44 | `teacher_id, first_name, last_name, department, rank, max_hours_per_week, email` |
| `courses.csv` | 32 | `course_id, code, title, department, programme_id, level, semester, credits` |
| `sessions.csv` | 218 | `session_id, course_id, group_id, teacher_id, session_type, duration_periods, occurrences_per_week, required_room_type, is_locked` |
| `rooms.csv` | 20 | `room_id, building, code, capacity, room_type, has_projector, has_computers` |
| `slots.csv` | 30 | `slot_id, day_index, day_name, period_index, period_label, start_time, end_time, is_open` |
| `teacher_availability.csv` | 157 | `availability_id, teacher_id, slot_id, is_available, semester, academic_year, source` |
| `holidays.csv` | 18 | `holiday_id, holiday_date, label, is_islamic, is_approximate, blocks_scheduling` |
| `calendar_config.csv` | 11 | `key, value` |
| `constraint_catalogue.csv` | 19 | `constraint_id, code, name, kind, default_weight, xhstt_ref, description` |

**Vocabulary is French and must not be translated in code.** `group_type` ∈ {`PROMO`, `TD`, `TP`};
`room_type` ∈ {`Amphi`, `Salle`, `Lab_Info`, `Lab_Sciences`}; `rank` ∈ {`Professeur`,
`Maitre de Conferences`, `Maitre Assistant`, `Assistant`} — unaccented, as the files carry them. The
domain enums mirror these literals exactly.

`calendar_config.csv` carries the slot formula itself:
`t = day_index * periods_per_day + period_index`, with 5 periods of 90 minutes over 6 days, Saturday
afternoon closed, Friday afternoon open, and the Ramadan window 2026-02-18 → 2026-03-19 shifting 60
minutes.

### Two schema facts that affect the model

**`occurrences_per_week` exists in `sessions.csv`.** It is 1 for every row today, but the column is
real. If it ever exceeds 1, H7 ("each session placed exactly once") no longer holds as written, and
the pre-analysis demand calculation changes with it. Read it; do not assume it away.

⚠️ **`is_available` is a boolean, and all 157 rows are 0.** They are unavailability declarations, as
documented — but there is **no way to express a preferred window**, while S5 "Teacher preference"
carries weight 0.20, the second highest of the seven. SRS §4.1 nonetheless specifies a grid marking
slots "available, unavailable **or preferred**". See **C-12**; it interacts badly with C-5.

### Personal data in the instance

`students.csv` carries `first_name` and `last_name`; `teachers.csv` adds `email`. The values are
generated, and committing them is fine — but the application **records no student name** (a student is
represented by their group outside the examination module), and **no name or address may ever enter
the assistant's context payload**. Load `student_id` and the group links; leave the rest.

---

## Why the data is generated

Three public sources were evaluated before any implementation. None could be merged with another —
identifiers do not correspond, levels of detail differ, and two Kaggle files are invalid.

More decisively, **none contains what the project needs most**:

- None distinguishes CM, TD and TP.
- None describes the hierarchy between a promotion, its groups and its subgroups.
- None contains a Tunisian calendar or a shortened-day period.
- None contains teacher-declared availability — which is precisely what the application collects.

### Role given to each source

| Source | Role | Loaded into the database |
|---|---|---|
| ITC-2007, Track 3 | Validate the course engine against published results — **used, 2026-07-31**: `optiedt.validation.itc2007`, `docs/testing-strategy.md` §1 | **No** |
| XHSTT-2014 | Catalogue of constraint types to support | **No** — transcribed into `constraint_catalogue.csv` |
| Kaggle, University Exam Scheduling | Reference for the examination model; rooms and enrolments only | **No** — increment 2 |
| ITC-2007, Track 1 | Validate the examination engine | **No** — increment 2, **not yet opened** |
| **Generated instance** | **The data the application runs on** | **Yes** |

Reading the XHSTT archive produced a deliverable rather than an import: `constraint_catalogue.csv`,
listing **19 constraints — 12 hard and 7 soft** — each with its corresponding XHSTT constraint type
where one exists. That file is the link between the published formalism and this project's model.

### What verification found

Three of the four archives are present in `data/reference/` and were re-verified on 2026-07-29 by
opening the files. Measured figures and the full record are in
[`data/reference/PROVENANCE.md`](../data/reference/PROVENANCE.md).

- **ITC-2007 Track 3** — clean and matching its description. **21 instances present.** No individual
  students, only per-course counts. Does not distinguish CM/TD/TP. What is held is a **source
  repository bundling the instances with a third-party solver**, not the competition archive itself —
  describe it that way. Its bundled validator and published results are what make the benchmark
  comparison possible, and 2026-07-31 they did exactly that: the validator's cost rules were
  transcribed into `optiedt/validation/itc2007/cost.py`, and the seven solutions it ships were
  re-evaluated to exactly the cost the bundled report publishes for them. **That agreement is what
  licenses quoting any figure from the benchmark.** The reference costs come from the report's own
  tables (`docs/latex/itc2007.tex`), which cover `comp01`–`comp07` only.
- **XHSTT-2014** — complete, but concerns secondary schools and is heavy to read. Its value is the
  *list of constraint types*. **25 instances in the version held** — announced counts vary between
  archive versions, so cite the catalogue that was read directly, never a count from a summary.
- **Kaggle** — ⚠️ **two files are unusable, and the archive claims the opposite.** Its own `note.txt`
  says *"Clean CSVs with full entity relationships."* Measured: **44 of 100 timeslot rows (44%) have
  an end time at or before their start time**; **2,380 of 2,853 room+slot pairs in `schedule.csv`
  (83%) host more than one course**; **2,637 of 4,173 instructor+slot pairs (63%) place the instructor
  in more than one room.** Only the room list and student enrolments are keepable.

  This is the concrete justification for refusing to merge: a file in which 83% of room-slot pairs are
  double-booked cannot serve as a reference for anything, and importing it would place conflicts inside
  the data meant to *be* the reference.

  ⚠️ **`students.csv` carries names, email addresses, phone numbers and postal addresses** across 3,000
  rows. The values look synthetic, but the file is personal-data-shaped. If any part of it is ever
  used, take `student_id` and course enrolment and nothing else — and never let a name or an address
  reach the assistant's context payload.
- **ITC-2007 Track 1** — **not present and not opened**. Verification is placed at the start of
  increment 2. **Assume no property of it before that verification.**

**The methodology earned its keep here.** The project's approach was to verify by reading the files
rather than their documentation, "because a dataset can be described as complete and contain errors."
The Kaggle archive describes itself as clean and is 44% invalid in one file and 83% inconsistent in
another.

ADR-008 records why no merge was attempted: it would have produced a set that is neither a valid
benchmark nor realistic data, with invalid rows sitting inside the reference.

---

## Content of the reference instance

Generated from the organisational rules of a faculty, not from a random draw.

| Element | Content |
|---|---|
| Programmes | 3 — Licence Informatique, Licence Mathématiques, Master Informatique |
| Promotions | 6, from L1 to M1, 40 to 120 students |
| Groups | **51** — 6 promotions, 15 tutorial groups, 30 laboratory subgroups |
| Students | **425**, each attached to a promotion, a tutorial group and a subgroup |
| Courses | 32, all of the second semester |
| Sessions | **218** — 32 CM, 82 TD, 104 TP |
| Session durations | 114 of one period, **104 of two consecutive periods** |
| Teachers | **44** — 7 professors, 11 senior lecturers, 13 assistant lecturers, 13 assistants |
| Maximum loads | 9, 12, 18 or 24 hours per week by rank |
| Rooms | **20** — 2 lecture theatres, 10 classrooms, 6 computer laboratories, 2 science laboratories |
| Room capacities | 20 to 250 places |
| Slot grid | 6 days × 5 periods of 90 minutes = **30 slots, 28 open** |
| Closed slots | The two Saturday afternoon periods |
| Holidays | 18 days blocking scheduling, **10 following the lunar calendar** |
| Shortened-day period | 18 February – 19 March 2026, 60-minute shift |
| Declared availability | **157 declarations covering 41 of the 44 teachers** |

Generation follows the LMD structure: programmes declined by level; each promotion divided into
tutorial groups of usual size; each group divided into laboratory subgroups; sessions created from
courses as one lecture per promotion, one tutorial per group, one laboratory session per subgroup.
Rooms are typed with capacities consistent with the groups that use them.

**Every availability row carries `SYNTHETIC` in its source column.** This matters for the honesty of
the demonstration: the application collects availability from a web form, and generated declarations
exist only so the instance is solvable before any teacher has connected. A generated declaration and a
real one must be distinguishable at any moment.

---

## The five verifications

Applied **before any solving**. Their purpose is to distinguish an instance that genuinely has no
solution from an error in the model — two situations a solver reports identically.

All five pass on the reference instance, with these results:

| Verification | Expected result |
|---|---|
| Each session finds a room of the required type and sufficient capacity | **0 sessions** without a suitable room |
| Open slots cover the demand for each room type — **two bounds, see below** | *Periods:* lecture theatres **57%** · classrooms **42%** · computer laboratories **71%** · science laboratories **57%**. *Two-period windows, the binding figure:* **computer laboratories 91%** · science laboratories **73%** |
| No teacher exceeds the maximum load of their rank | **0 teachers** above the limit; heaviest load 12 periods (18 hours) |
| Each teacher keeps enough free slots for their assigned sessions | **0 teachers** in difficulty; smallest margin **11 free slots** |
| The group hierarchy is consistent | **0 invalid references, 0 invalid chains**; 425 students matching declared group sizes exactly |

A failing verification **names the resource concerned and the quantity missing** — that is the content
of the report required by FR-12, not a boolean.

### ⚠️ 91% is the number to watch — and counting periods will not show it to you

Computer laboratories at **91% of their two-period windows** are the tightest point of the instance and
the one most likely to make the problem infeasible if a room is withdrawn.

**Why "windows" and not "periods".** A two-period session needs its periods *consecutive* and inside
*one day*: H8 forbids crossing a day boundary, H9 forbids closed slots. So the week's open slots are
not a flat pool but six contiguous runs — five of length 5, one of length 3 — and a run of length `L`
offers a room only `floor(L/2)` disjoint two-period windows. **One room offers 11 a week, not 28
periods' worth.** With 5-period days and 2-period laboratory sessions, one period per room-day is
structurally unusable: a fifth of the apparent capacity does not exist.

Counting periods is therefore **necessary but not sufficient**, and the difference is not academic. The
instance as first generated had 6 computer laboratories: 160 / 168 periods = a comfortable **95.2%**,
against 80 sessions needing 66 windows — **short by 14, with no solution at all**. It passed
verification, and the resulting `UNKNOWN` from the solver was diagnosed for three sessions as a
search-performance problem before anyone checked whether a solution existed (C-13). The repair re-typed
three classrooms as laboratories. **Both bounds are now checked, and any new check must state which
kind it is.**

The practical consequence for development: **at that saturation, a modelling regression surfaces as
`INFEASIBLE`, not as a slow solve.** An over-tight domain restriction or a wrong channelling constraint
looks exactly like an instance with no solution. The pre-analysis is the primary debugging instrument
of this project, not a nicety — it is how you tell the two apart. Run it first, always.

Record this figure whenever the instance is modified.

---

## Layout

```
data/
  generator/      Produces the 13 files. Imports NOTHING from backend/    ← to be written
  instance/       The 13 CSVs + constraint_catalogue.csv                  ← to be generated
  reference/      ITC-2007 · XHSTT · Kaggle — present, gitignored         ✅ verified
  verification/   The five checks and their expected results              ← to be written
```

**`data/generator/` imports nothing from `backend/`.** The 13 files are the contract between the
generator and the application. If the generator imported the ORM, the file schema would stop being the
interface and the instance would become an implementation detail of the backend — which would make it
impossible to hand the instance to anyone, or to validate it independently.

`data/reference/` is gitignored: those archives carry their own licences and, per ADR-008, have a
validation role only. **Three of the four are already present** — see
[`PROVENANCE.md`](../data/reference/PROVENANCE.md). Only ITC-2007 Track 1 is missing, and it is not
needed until increment 2.

---

## Data required by weight adjustment

Adjusting weights automatically would require a collection of timetables accepted or refused by a
department, with the reason for each decision.

**No such collection exists for a Tunisian faculty, and it cannot be reconstructed after the fact** —
published timetables from past years carry no trace of the alternatives that were set aside.

Two consequences, both accepted:

1. Weights start at the catalogue values, which are the only ones available and already give a usable
   order.
2. **The application is, from its first use, the instrument that produces the missing data.** Each time
   the person in charge examines two candidates and retains one, that choice is recorded as a
   comparison. After enough of them, an adjustment becomes possible — and is evaluated before being
   adopted.
