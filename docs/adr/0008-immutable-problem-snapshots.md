# ADR 0008 — Immutable problem snapshots as the basis of every result

**Status:** Accepted

## Context

Academic data keeps changing while candidates are reviewed. A published timetable must remain
interpretable and reproducible after rooms are renamed or activities removed.

## Decision

- When a run is requested, the live data of the term is compiled into a **problem snapshot**:
  canonical JSON containing every entity the problem references, stored with its SHA-256
  content hash (identical data reuses the same snapshot).
- Session identities are deterministic: `uuid5(activity_id, occurrence)`, so the same activity
  keeps the same session identifiers across snapshots.
- Solutions store only assignments (session → day, period, room) and reference a snapshot.
  Publications copy their assignments and reference their snapshot.
- **Rebasing** maps a solution onto a newer snapshot by session identifier and re-validates it;
  this is how data changes after publication become visible as violations.

## Consequences

- History never breaks when live records are edited or deleted.
- Rendering a solution loads its snapshot; snapshots are cached in-process by hash.
- Snapshot size is proportional to the term's data (roughly 1–3 MB for large institutions).
