# ADR 0017 — Weekly-recurring timetables; no alternating-week patterns in v1

**Status:** Accepted

## Context

Most programme-based institutions publish one weekly pattern per term. Some alternate lab
groups between odd and even weeks.

## Decision

- A term has one weekly pattern repeated over its teaching dates, minus holidays and closures,
  with date-level exceptions (ADR 0013) and timing variants (e.g. Ramadan hours) applied to
  dated occurrences.
- Alternating-week or week-range patterns are not modelled in the solver in this release.

## Consequences

- Institutions that alternate groups by week model the alternation as two groups sharing a
  slot manually, or schedule them separately. Recorded in `docs/product/known-limitations.md`.
