# Domain model

The **session** is the centre of the model. It is the unit CP-SAT places; every other entity either
describes a session or constrains it.

---

## Canonical names

French LMD terms keep their French names in code. They are precise terms of art with no clean English
equivalent, and translating them invites two sessions to use two different words for one thing.

| Domain term | Code identifier | Meaning |
|---|---|---|
| Filière / programme | `Programme` | Field of study in the LMD structure |
| Promotion | `Promotion` | Annual cohort of a programme (L1, L2, M1 …) |
| Groupe | `Group` | Promotion, tutorial group, or laboratory subgroup — one entity, three levels |
| CM | `SessionType.CM` | *Cours magistral* — lecture, whole promotion, lecture theatre |
| TD | `SessionType.TD` | *Travaux dirigés* — tutorial, one group, ordinary classroom |
| TP | `SessionType.TP` | *Travaux pratiques* — laboratory session, one subgroup, equipped room |
| Créneau | `Slot` | Time unit of the weekly grid, single integer index |
| Séance | `Session` | The unit to be placed: course + group + teacher + duration |

Deliberately **not** renamed: `Promotion` is not `Cohort`, `Group` is not `Class`, and CM/TD/TP are not
`LECTURE`/`TUTORIAL`/`LAB`. The catalogue, the instance CSVs and the specification all use the French
codes; renaming in code alone would create a translation layer with no benefit.

Other fixed vocabulary:

| Term | Meaning |
|---|---|
| **Run** | One execution of the generation, with its data, seed, weights and results |
| **Weight profile** | Non-negative weights over the soft criteria, normalised to sum to 1 |
| **Candidate** | A valid timetable produced by one run under one profile |
| **Portfolio** | The set of candidates produced by one run |
| **Sub-score** | One criterion's value for one candidate, brought into [0, 1] |
| **Contribution** | The part of the difference between two scores attributable to one criterion |
| **Dominated candidate** | One that another candidate improves on **every** criterion |
| **Comparison** | The recorded choice when the person in charge retains one candidate over another |

---

## Entities

### Structure of the teaching

| Entity | Key attributes | Role |
|---|---|---|
| `Programme` | code, label, degree cycle, department | Field of study |
| `Promotion` | programme, level, academic year, size | Annual cohort |
| `Group` | promotion, **parent_group**, type, label, size | Promotion / tutorial group / subgroup |
| `Student` | promotion, tutorial group, laboratory subgroup | Individual. **Used only by the examination model** |
| `Teacher` | department, rank, max hours per week | Person responsible for sessions |
| `Course` | code, department, programme, level, semester, credits | Teaching unit |
| `Session` | course, group, teacher, type, duration, required room type, **locked** | **The unit to be placed** |
| `Room` | building, code, capacity, type, equipment | Where a session is held |

### Time and calendar

| Entity | Key attributes | Role |
|---|---|---|
| `Slot` | day index, period index, start/end hour, **is_open** | Time unit of the weekly grid |
| `Availability` | teacher, slot, state, semester, **source** | Declaration by a teacher, or generated |
| `Holiday` | date, label, lunar, approximate, blocking | Day on which nothing is placed |
| `CalendarConfig` | key, value | Periods per day, closed half-days, shortened-day window |
| `Constraint` | code, name, kind, default weight, XHSTT reference | The catalogue of supported rules |

### Runs and results

| Entity | Key attributes | Role |
|---|---|---|
| `Run` | date, seed, time budget, state, model version | One execution of the generation |
| `WeightProfile` | name, weight per criterion | The weights used to produce a candidate |
| `Candidate` | run, profile, cost, score | A valid timetable |
| `Placement` | candidate, session, slot, room | One assignment inside one candidate |
| `SubScore` | candidate, criterion, raw value, normalised value | One criterion's value for one candidate |
| `Comparison` | run, candidate retained, candidate set aside, user, date | A recorded preference |
| `Recommendation` | candidate, criterion, action type, parameters, status, resulting candidate | An AI proposal and its outcome |
| `Publication` | candidate, date, user | A timetable made visible to teachers and students |

---

## Rules of the model

### The group hierarchy

A `Group` refers to its parent group. Exactly one chain is admitted:

```
Promotion  →  tutorial group  →  laboratory subgroup
```

This is what makes H12 expressible. In the LMD organisation a **CM gathers the whole promotion**,
while TD and TP concern its groups and subgroups. When a lecture is placed, every student of every
subgroup is occupied, so no session of any of those subgroups may share the slot. A model treating
sessions as independent events misses this and produces timetables that are impossible in practice.

Reference instance: 51 groups — 6 promotions, 15 tutorial groups, 30 laboratory subgroups.

### Slot indexing

```
slot = day_index × periods_per_day + period_index
```

A single integer index reduces the placement of a session to one integer variable. The reference grid
is 6 days × 5 periods of 90 minutes = 30 slots, of which 28 are open.

### Configuration as data — never as a constraint

Holidays, closed half-days and the shortened-day window live in `CalendarConfig`, never in the model.
They act in exactly two ways:

- **Closing slots** — sets `Slot.is_open = false`; H9 then removes those slots from every session's
  domain. No new rule is written.
- **Shifting hours** — moves the start and end hour of each period by a configured number of minutes.
  **The slot index does not change**, so no variable and no constraint is affected; only displayed and
  printed hours differ.

A rule written into the model cannot be changed by the department; a rule held as data can. Ramadan
moves ~11 days a year and closed half-days are a local decision — writing them into the model would
force the department to call a developer to apply its own decision. See ADR-003, which also records the
condition for promoting such a rule to a hard constraint: **written confirmation from the institution**
that it may never be violated.

### Origin of a declaration

Every `Availability` row carries its source. Generated rows carry `SYNTHETIC`. This matters for the
honesty of the demonstration: the application collects availability from a web form, and generated
declarations exist only so the instance is solvable before any teacher has connected. A generated and a
real declaration must be distinguishable at any moment.

### Immutability of a candidate

A candidate is never modified after being recorded. Its sub-scores describe its content; editing it
would leave them describing something that no longer exists. **A regenerated timetable is a new
candidate under a new run** — never an edit to an existing one.

### Bounds recorded with the run

The bounds used to bring criteria into [0, 1] are **derived from the instance**, not from the
candidates produced, and are recorded with the run so a score can be recomputed later exactly as it was
displayed. See ADR-009 — the candidate-derived alternative breaks the monotonicity property the
specification requires, and silently invalidates cross-run comparison.

### How the entities are stored · Phase 5 M3

`backend/src/optiedt/db/models.py`, first migration `5d1497398fab`. **Normalised where this document
names an entity** — `runs`, `run_weights`, `candidates`, `placements`, `sub_scores`, `run_checks`,
`run_diagnoses`, `availability_declarations` — because those are the things a later question gets
asked about. Two short ordered lists of scalars stay as JSON columns (`duplicates_removed`, a
diagnosis's `conflicting_codes`): nothing joins to them, and a table each would add joins for no
question anyone asks.

Three rules the schema carries rather than assumes:

- **Candidate order is data.** `candidates.rank_order` preserves the ranking the run produced, because
  the interface displays that order and must not sort for itself. Read back with `ORDER BY`.
- **Invariant 6 is enforced by omission.** No code path updates a candidate, a placement or a
  sub-score; they are inserted once, when a run first carries them.
- **A teacher who declared nothing is not a teacher who was never asked.** An empty declaration is
  recorded with a marker row, so that "I am free all week" withdraws the generated rows while "not yet
  asked" leaves them standing — the distinction "Origin of a declaration" above requires.

### Traceability of a publication

A published timetable refers to the candidate, the run, the seed and the weights that produced it.
Every published timetable must be traceable back to its origin — this is an acceptance criterion, not a
convenience.

---

## Roles and rights

| Role | Rights |
|---|---|
| **Person in charge of the timetable** | Read and write on **all** data; launch runs; compare; publish |
| **Teacher** | Read and write own availability; read own timetable and supervised examinations |
| **Student** | Read the timetable of their group |
| **Administrator** | Manage accounts, holidays and the academic calendar |

**Implemented in Phase 5 M4 (FR-11).** A bearer token carries the username, the role and — for a
teacher — the `teacher_id` their account owns. `api/deps.py` declares the rights per endpoint rather
than centrally, so a router that must name who may call it cannot acquire a caller by accident.

⚠️ **The administrator's account-management right is NOT implemented.** Accounts come from a seed
command (C-18) because no requirement describes registration and the instance carries no user data.
That is recorded rather than quietly dropped; it belongs with FR-1's data management.

⚠️ **A teacher account with no `teacher` link is refused every grid**, rather than defaulted to one.
An account that cannot say whose week it owns has no business editing one, and a default would hand
it somebody else's.

**Resolved contradiction.** The Cahier des Charges §4.3 and SRS §3.3 both describe *the administrator*
loading the department data, while SRS Table 2 gives that right to the person in charge and limits the
administrator to accounts and calendar. **SRS Table 2 is authoritative**; the two flow sentences are
imprecise prose. Recorded as C-8 in `docs/open-questions.md`.

**Head of department.** CdC Table 1 lists a fifth actor who "examines the teaching loads and approves
the timetable". This actor appears in no other document and has no requirement, no right, no screen and
no acceptance test. Treated as an **out-of-system stakeholder** until stated otherwise.

---

## Entity-relationship sketch

```
Programme ─┬─< Promotion ─┬─< Group ─────< Session >─── Course
           │              │        └─(parent_group, self-reference)
           │              └─< Student            │
           │                                     ├──> Teacher
           │                                     └──> Room (required type)
           └─< Course

Slot >──< Availability >──── Teacher
Slot ───(is_open ← CalendarConfig, Holiday)

Run ─┬─< Candidate ─┬─< Placement ──> Session, Slot, Room
     │              ├─< SubScore ────> Constraint
     │              ├─< Recommendation ──> resulting Candidate
     │              └─── Publication
     ├─── WeightProfile
     └─< Comparison ──> Candidate (retained), Candidate (set aside)
```
