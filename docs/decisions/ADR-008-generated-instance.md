# ADR-008 — Generated instance; public sources given roles, never merged

**Status:** Accepted
**Date:** 2026-07-23 (specification phase)

## Context

An engine of this kind cannot be developed without data. Before writing any code, the public timetabling
datasets were searched, downloaded, and **opened and verified** — by reading the files themselves rather
than their documentation, because a dataset can be described as complete and contain errors.

The first idea was to merge the sources into a single database. Verification showed it is not possible.

## Decision

**Each public source is given one role. The application runs on an instance generated for it.**

| Source | Role | Loaded |
|---|---|---|
| ITC-2007 Track 3 | Validate the course engine against published results | No |
| XHSTT-2014 | Catalogue of constraint types to support | No — transcribed into `constraint_catalogue.csv` |
| Kaggle exam scheduling | Reference for the examination model; rooms and enrolments only | No — increment 2 |
| ITC-2007 Track 1 | Validate the examination engine | No — increment 2, not yet opened |
| **Generated instance** | **The data the application runs on** | **Yes** |

## Consequences

**Why merging was rejected — three findings, each sufficient on its own:**

1. **Identifiers do not correspond.** A teacher is a code in one dataset, a long identifier in another,
   a name in the third. Nothing establishes that two records designate the same person.
2. **Levels of detail differ.** The competition dataset reasons on courses and gives only student
   counts; the Kaggle dataset gives each student individually. Merging would require **inventing the
   missing information**.
3. **Two Kaggle files are invalid.** The timetable file contains rooms occupied twice at the same moment
   and teachers in two rooms at once; the slot file contains rows whose end hour precedes its start hour.
   Merging would place **conflicts inside the data meant to serve as reference**.

Merging would have produced a set that is neither a valid benchmark nor realistic data.

**Why generation is necessary regardless of merging.** None of the sources contains what the project
needs most: none distinguishes CM, TD and TP; none describes the promotion→group→subgroup hierarchy;
none contains a Tunisian calendar or a shortened-day period; and none contains teacher-declared
availability — **which is precisely the information the application exists to collect**.

**The condition attached to generation.** This is a normal situation in the field **on condition that
the generated data is not invented at random and is verified before use**. Generation follows the
organisational rules of a faculty, and five verifications are applied before any solving.

**The binding this creates.** The documents state the verification results as facts — 0 sessions without
a suitable room, 95% laboratory occupancy, heaviest load 12 periods, 425 students matching declared group
sizes. **The generator must therefore reproduce *the* documented instance, not merely a valid one**, or
the delivered documentation becomes false. Tracked as C-11.

> ⚠️ **Correction, 2026-07-30 (C-13) — read before writing the generator.** Two of the figures quoted
> above are the PDFs' superseded values, kept here because this ADR records the reasoning as it stood.
> The room mix is **Amphi 2 · Salle 7 · Lab_Info 8 · Lab_Sciences 3** (total still 20), not 2 / 10 / 6 / 2,
> and laboratory occupancy is **91% of two-period windows** (71% of periods), not 95%. **The original mix
> made the instance infeasible** — every laboratory session spans two periods, so a room offers 11
> two-period windows a week, not 28 periods, and 6 computer laboratories offered 66 against 80 needed.
> **A generator reproducing the figures as literally written above would emit an instance with no
> solution.** The replacements are in the ERRATA table of `docs/open-questions.md` (CdC Tables 10 and 11).

**Honesty markers.** Every generated availability row carries `SYNTHETIC` in its source column, so a
generated declaration and a real one are distinguishable at any moment. The ITC-2007 Track 3 folder is
described as **a source repository bundling the instances with a third-party solver**, not as the
competition archive itself. XHSTT instance and country counts vary between archive versions, so the
documentation cites the catalogue that was read directly, never a count from a summary.

**ITC-2007 Track 1 has not been opened.** Its verification is placed at the start of increment 2, and
**no property of it is assumed before then**.

## Alternatives considered

**Merge all sources into one database** — **rejected**, three reasons above.

**Use ITC-2007 Track 3 directly as the application's data** — **rejected**: no CM/TD/TP distinction, no
group hierarchy, no calendar, no availability. It remains the validation benchmark, which is the role it
can actually fill.

**Use real data from a Tunisian faculty** — none was available for the project.

## References

Project Plan and Methodology §3.1–3.7 · Cahier des Charges §8.1–8.3
