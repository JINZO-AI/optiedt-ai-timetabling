# ADR-013 — Examinations are derived from the instance, never supplied

**Status:** Accepted
**Date:** 2026-08-12 (Phase 13)
**Question:** C-23

## Context

**SRS §3.2, Table 19 states FR-20 in full**, and it was located in Phase 13 after
four phases in which this repository recorded FR-20 as unspecified:

| | The supervisor's own words (SRS §3.2, Table 19) |
|---|---|
| **Input** | Examinations, students, rooms, period of the session and supervisors |
| **Processing** | Construction of the model of section 6.8 then solving |
| **Output** | One slot and one or more rooms assigned to each examination |

Five inputs. The repository supplies **two** of them:

- ✅ **students** — `students.csv`, 425 rows, and a `Student` entity that has
  existed since Phase 1 carrying a docstring naming X1.
- ✅ **rooms** — `rooms.csv`.
- ❌ **examinations** — no file, no entity. **SRS Table 25, "Main entities of
  the data model", defines no Examination entity.**
- ❌ **period of the session** — `calendar_config.csv` carries the academic
  year, the semester and the Ramadan window, and no examination dates.
- ❌ **supervisors** — no file, no entity, no column. The word "supervisor"
  appears in the entire SRS **only inside X4's own statement**.

So three of FR-20's five stated inputs have no source anywhere in the
specification or the data. This is a **silence**, not a contradiction — the
same shape as C-22, which Phase 12 raised and settled the same way.

⚠️ The specification does supply one constraining fact, under its assumptions:
*"The examinations of a session concern the same population as the semester."*

## Decision

**Examinations are DERIVED from the instance already loaded. No examination
data is imported, and no examination-data form is built.**

Three rules, each settled by a measurement on the reference instance rather
than by preference:

### 1 · One examination per course

Measured: **no course spans more than one promotion** (0 of 32), and a course's
own `programme`/`level` agrees with its sessions' promotion in **every** case
(0 mismatches). So "one examination per course" and "one per (course,
promotion)" name the same 32 examinations here, and the simpler rule is the one
that cannot be wrong about this data.

⚠️ **A future instance sharing a course between promotions is REFUSED, not
guessed.** `derive_examination_session` raises naming the course and saying
that the per-(course, promotion) rule is a decision for the project owner.

### 2 · The supervisor is the course's CM teacher

Measured: a course has **3 to 13 distinct teachers** once TD and TP groups are
counted, and **exactly one CM** (32 of 32). "The course teacher" is therefore
ambiguous and "the CM teacher" is not. The CdC grants a teacher *"consultation
of the personal timetable and of the examinations supervised"*, so a teacher IS
a supervisor; which one is what the data had to settle.

### 3 · The period is two calendar-configuration keys

`exam_period_start` and `exam_period_days`, added to `calendar_config.csv`.
Configuration rather than constraint, which is **invariant 7**: a day outside
the period produces no `ExamSlot` at all, so X3 holds by the domain of the
variable, exactly as H9 works weekly.

## Consequences

**What this buys.** FR-1 is untouched — its eleven-file contract, its 34
acceptance tests and its 39 detected mutations all stand. No import path is
added, no file format is invented, and SRS §4.1's enumeration of nine user
interfaces (which names **no** data-management form, and which is what settled
Phase 12's no-CRUD decision) is respected.

**What it costs, stated plainly.** ⚠️ **A department dataset supplied through
FR-1 carries no roster**, because `students.csv` is not one of the eleven files
that contract admits. X1 and X2 are both about students, so an examination
session on such a dataset is **refused with that reason in words**, not solved
against zero candidates. `test_a_dataset_without_a_roster_is_refused_with_the_reason`
pins it, including that the message names the file.

**What would reverse this.** A supervisor statement that examinations are
supplied data, or a requirement for per-(course, promotion) examinations. Both
would change the derivation, neither would change the solver: `ExamSession` is
the seam, and `derive.py` is the only thing that would move.

## Alternatives considered

**Extend FR-1's dataset with examination, supervisor and period files** —
**rejected.** It would take a `✓` requirement's contract from eleven files to
thirteen or more, invent three file formats the specification never describes,
and build precisely the examination-data upload system SRS §4.1's silence
argues against. The literal reading of "Input" is the argument for it, and it
loses to the cost.

**Take examinations from the Kaggle exam dataset** — **rejected.** ADR-008
gives that source "rooms and enrolments only", and `PROVENANCE.md` measured its
schedule file as 83 % double-booked. Merging it was already rejected for three
reasons that all still hold.

**Ask the supervisor** — the standing situation on this project is that the
supervisor does not answer (C-9, C-22), and the project owner has directed that
such questions be settled from repository evidence and recorded as project
decisions. That is what this is.

## References

SRS §3.2 Table 19 · SRS §6.8 Table 30 · SRS Table 25 · SRS §4.1 · SRS §5.5 ·
CdC §5.5 Table 6 · PPM increment 2 · C-22 and ADR-012 (the same shape, one
phase earlier) · C-8 (Table 2 wins over flow prose) · R-6
