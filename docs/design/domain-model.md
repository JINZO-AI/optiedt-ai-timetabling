# Domain model

The model separates **reference data** that persists across terms, **term data** that
describes one term's teaching, and **scheduling results** that are derived from immutable
snapshots of term data.

```
Institution (singleton settings)
├── Department (tree: faculty → department)
├── Campus ── Building ── Room ──< RoomFeature
│      └── CampusTravelTime            └── RoomType
├── Programme (belongs to Department)
├── Course (belongs to Department)
├── ActivityType (Lecture/CM, Tutorial/TD, Lab/TP …)
├── Instructor (belongs to Department)
├── CalendarEvent (holidays and closures by date)
├── User ──< RoleAssignment (role, optional department scope)
│
└── Term
    ├── TimeGrid: weekdays, Period[] (times, joinable-with-next), closed slots,
    │             per-weekday time overrides, slot penalties, TimingVariant[] (date ranges)
    ├── StudentGroup (tree with partition keys; size)
    ├── Activity ──< Session (derived: one per weekly occurrence)
    │     ├── groups[], instructors[], required features[], room preferences[]
    │     └── FixedPlacement[] (per occurrence)
    ├── AvailabilityGrid (instructor | group | room | activity) — per period state
    ├── ConstraintRule[] (type, hard/soft, tier, weight, parameters, scope)
    ├── ObjectiveProfile[]
    ├── Scenario ──< SolverRun ──< SolverRunEvent
    │                    └── ProblemSnapshot (immutable, content-hashed)
    ├── Solution (candidate / draft) ──< Assignment, ChangeLogEntry
    └── Publication (numbered, immutable) ──< PublishedAssignment, OccurrenceException
```

## Reference data

| Entity | Key attributes | Rules |
|---|---|---|
| Institution | name, short name, country, timezone, default locale, enabled locales, week start, date/time format, public timetable flag, approval-required flag | Exactly one row |
| Department | code, name, parent | Tree; scope of access control |
| Campus | code, name, address | Travel times between campuses in minutes |
| Building | campus, code, name | Code unique within campus |
| RoomType | code, name | e.g. `LECTURE_HALL`, `CLASSROOM`, `COMPUTER_LAB` — data, never enums |
| RoomFeature | code, name | e.g. projector, computers, wheelchair access |
| Room | building, code, name, type, capacity, features, owning department (optional), active | Capacity > 0; code unique within building |
| Programme | code, name, department, level | |
| Course | code, title, department, credits, active | Code unique |
| ActivityType | code, name, default room type, colour | e.g. `CM`, `TD`, `TP` or `LEC`, `TUT`, `LAB` |
| Instructor | staff code, names, email, department, title, maximum weekly periods, active | Code unique |
| CalendarEvent | date range, kind (holiday / closure), label, tentative | Tentative marks dates known only approximately (lunar holidays) |

## Term data

### Time grid

A term defines its teaching **weekdays** (any subset of the week, in display order) and an
ordered list of **periods**, each with start and end time and a `joins_next` flag stating
whether a multi-period session may continue into the next period. A **slot** is a
(weekday, period) pair.

- Individual slots can be **closed** (e.g. Saturday afternoon, Wednesday afternoon sports).
- Slot times can be **overridden per weekday** (e.g. Friday afternoon starts later).
- Slots can carry an institution-level **penalty** (0–3) used by the "undesirable periods"
  objective (late evening, Saturday).
- **Timing variants** override period times for a date range (e.g. Ramadan hours). They change
  dated occurrences and documents, never the weekly placement.

### Student groups

A tree of groups per term, each with a size. Each child has a **partition key**: children of
the same parent sharing a key are disjoint sets of students (tutorial groups G1…G4); children
with different keys overlap (language options vs. tutorial groups). See ADR 0011.

Conflict rule: groups A and B share students iff one is an ancestor-or-self of the other, or
the children of their lowest common ancestor on the two paths have different partition keys.

### Activities and sessions

An **activity** is one kind of teaching of one course for a set of student groups: "ALG201
Lecture for L2 Computer Science", "ALG201 Tutorial for group G3". Attributes:

| Attribute | Meaning |
|---|---|
| course, activity type | What is taught |
| groups | Student groups attending together (at least one) |
| instructors | All attend every session (co-teaching); zero allowed for self-study blocks |
| duration | Consecutive periods per session (≥ 1) |
| sessions per week | Weekly occurrences (≥ 1) |
| different days | Occurrences on different days (default true when > 1 session) |
| delivery mode | `in_person` needs a room; `online` needs none but still occupies people |
| room type, required features | Room compatibility; type defaults from the activity type |
| minimum capacity | Default: sum of group sizes |
| campus / building | Optional restriction |
| room preferences | Allowed (restrict to these), preferred, avoided rooms |
| fixed placements | Per occurrence: slot, optionally room |
| time preferences | Availability grid of the activity (unavailable / undesirable / preferred slots) |

A **session** is one weekly occurrence of an activity, identified by
`uuid5(activity_id, occurrence_number)` so identities are stable across snapshots.

### Availability grids

Per term and per resource (instructor, group, room, activity): a sparse map from slot to
state. States: `available` (default), `preferred`, `undesirable`, `unavailable`. Instructors
declare their own grid while the term's declaration window is open.

### Constraint rules and objective profiles

A **constraint rule** is an instance of a rule type from the catalogue
(`docs/design/optimization-model.md` §4) with parameters, a scope (targets), enforcement
(`hard` or `soft`) and, when soft, a tier and weight. An **objective profile** assigns tiers
and weights to the built-in objectives. Both are term data and enter the snapshot.

## Scheduling results

| Entity | Purpose |
|---|---|
| ProblemSnapshot | Canonical JSON of everything a run needs; SHA-256 addressed; immutable |
| Scenario | Named configuration: profiles to generate, scope, reference solution, solver settings |
| SolverRun | One execution: frozen configuration, snapshot, status, phase, progress, lease, logs, result summary |
| SolverRunEvent | Timeline: phases, incumbents, bounds, tier completions, warnings |
| Solution | A timetable over a snapshot: assignments, status (`draft`, `pending_approval`, `approved`, `published`, `archived`), evaluation, lineage (run, parent solution, base publication) |
| Assignment | Session → (day index, period index, room or none), locked flag |
| ChangeLogEntry | One edit: actor, time, kind, session, before, after, reason, affected resources |
| Publication | Term version *n*: copied assignments, snapshot, author, note, supersedes |
| OccurrenceException | Date-level change of one occurrence: cancel, relocate, reschedule |
| AuditEvent | Append-only record of every change in the system |

Status rules:

- A solution is **valid** when every snapshot session is assigned and the evaluator finds no hard
  violation. Only valid solutions can be submitted, approved or published.
- `approved` and `published` solutions are read-only. Editing one creates a new draft whose
  parent is it and whose base publication is the one it came from.
- A publication is never modified. Restoring version *k* creates version *n+1* with *k*'s content.

## Identity and deletion

- UUID identifiers everywhere.
- Reference data in use by current term data cannot be deleted (foreign keys `RESTRICT`); it can
  be deactivated. Historical results are unaffected by deletion because snapshots are
  self-contained.
- Editable records carry a `version` counter for optimistic concurrency; a stale update is
  rejected with `409 Conflict`.
