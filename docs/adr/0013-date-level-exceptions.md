# ADR 0013 — Date-level exceptions on published timetables

**Status:** Accepted

## Context

Day-to-day disruptions ("Room B is unavailable tomorrow", "Dr. X is ill on Thursday") must
not force a new weekly timetable.

## Decision

- An **exception** changes one occurrence of a session on one date: cancel, relocate (another
  room, same time) or reschedule (another period in the same teaching week).
- A disruption assistant takes a resource and a date range, lists affected occurrences, and
  proposes per occurrence the least disruptive valid option (same time different room first,
  then other times), validated against the published timetable plus other exceptions.
- Exceptions belong to a publication version. Publishing a new version carries forward
  exceptions whose session keeps its weekly placement and reports the others.

## Consequences

- Dated views (today, a given week) and calendar feeds apply exceptions; weekly views show the
  standard pattern and mark weeks with changes.
