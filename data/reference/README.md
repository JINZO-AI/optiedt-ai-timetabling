# Reference archives

**Present and verified.** See **[PROVENANCE.md](PROVENANCE.md)** for the measured
findings, the exact counts and the privacy note.

**Gitignored.** These carry their own licences and are never committed, never
loaded into the database, and never merged with the generated instance (ADR-008).

| Archive | Role | Status |
|---|---|---|
| ITC-2007 Track 3 (curriculum-based) | Validate the course engine against published results | ✅ Present, 21 instances |
| XHSTT-2014 | Catalogue of constraint types → `constraint_catalogue.csv` | ✅ Present, 25 instances |
| Kaggle, University Exam Scheduling | Reference for the examination model — rooms and enrolments only | ⚠️ Present, 2 files invalid |
| ITC-2007 Track 1 (examinations) | Validate the examination engine | ❌ **Not present, not opened** |

## What verification found

Recorded so nobody re-derives it, and so nobody treats these files as cleaner
than they are.

- **ITC-2007 Track 3** — clean and matching its description. No individual
  students, only per-course counts; no CM/TD/TP distinction. What is held is a
  **source repository bundling the instances with a third-party solver**, not
  the competition archive itself. Describe it that way. Its bundled validator and
  published results are what make the benchmark comparison possible.
- **XHSTT-2014** — complete, but concerns secondary schools and is heavy to
  read. Its value is the *list of constraint types*, not its content. 25
  instances **in the version held** — the announced counts vary between versions,
  so cite the catalogue that was read directly, never a count from a summary.
- **Kaggle** — ⚠️ **two files are unusable, and the archive claims otherwise.**
  Its own `note.txt` says *"Clean CSVs"*. Measured: **44% of timeslot rows have
  an end time at or before their start time**, and **83% of room+slot pairs in
  `schedule.csv` host more than one course**. Only the room list and student
  enrolments are keepable.
  ⚠️ `students.csv` carries names, emails, phone numbers and addresses — see the
  privacy note in PROVENANCE.md before touching it.
- **ITC-2007 Track 1** — **not present and not opened**. Verify it at the start
  of increment 2 before assuming anything about it.

## Why these are never merged

Identifiers do not correspond between sources; levels of detail differ (courses
with student counts versus individual students); and two Kaggle files are
invalid. Merging would place conflicts inside the data meant to serve as
reference, producing a set that is neither a valid benchmark nor realistic data.

See ADR-008.
