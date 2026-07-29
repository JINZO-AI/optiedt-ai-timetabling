# Constraint model

The decision layer. This is the only part of the system that assigns a slot and a room to a session,
and the only part whose correctness is guaranteed by construction rather than by testing.

Five of the twenty days of increment 1 are budgeted here. It carries the most uncertainty in the
project.

---

## Decision variables

| Variable | Type | Domain | Role |
|---|---|---|---|
| `start[s]` | Integer | Open slots compatible with `s` | The slot where session `s` begins |
| `room[s]` | Integer | Rooms of the required type and sufficient capacity | The room assigned to `s` |
| `iv[s]` | Interval | Built from `start[s]` and the duration | Occupation of `s` in time |
| `y[s][t]` | Boolean | 0 or 1 | Session `s` **occupies** slot `t` |

Interval variables are required because OR-Tools' non-overlap constraint operates on intervals, not on
separate start and end variables.

### `y[s][t]` — read this before touching it

`y[s][t]` is up to **6,104 booleans** (218 sessions × 28 open slots) and is the dominant term in model
size. Two things about it are commonly got wrong:

1. **Its purpose is soft-constraint accounting, not H7.** SRS Table 27 attributes H7 to it, but with
   `start[s]` an integer over a pruned domain each session already has exactly one start, so H7 is very
   nearly free. What actually needs `y` is idle time per group per day, days of presence, and spread —
   the objective, not feasibility.

2. **`y[s][t]` means *occupies* t, not *starts at* t.** **104 of the 218 sessions span two periods.**
   For a 2-period session starting at `t`, both `y[s][t]` and `y[s][t+1]` are true.

⚠️ **The channelling constraint linking `start[s]`, `iv[s]` and `y[s][t]` across a multi-period
duration is not specified anywhere in the three PDFs.** It must be written before the objective can be
encoded. Tracked as **C-7** in `docs/open-questions.md`.

The effective count is well below 6,104 because H4–H10 prune domains before search. 6,104 is recorded
as an upper bound, never as an estimate.

---

## Hard constraints

Every accepted timetable satisfies all twelve. Codes are permanent identifiers used in
`constraint_catalogue.csv`, in the conflict report and in `weight_delta` parameters — **never reuse a
retired code**.

| Code | Statement | Construction |
|---|---|---|
| **H1** | A teacher has at most one session per slot | NoOverlap on each teacher's intervals |
| **H2** | A group has at most one session per slot | NoOverlap on each group's intervals |
| **H3** | A room hosts at most one session per slot | NoOverlap on each room's intervals |
| **H4** | The session is in a room of the required type | Domain restriction on `room[s]` |
| **H5** | Room capacity covers the group size | Domain restriction on `room[s]` |
| **H6** | Teacher-declared unavailability is respected | Domain restriction on `start[s]` |
| **H7** | Each session is placed exactly once | Exactly-one over `y[s][t]` |
| **H8** | A multi-period session stays within one day | Withdraw end-of-day slots from `start[s]` |
| **H9** | No session on a closed slot or a holiday | Domain restriction on `start[s]` |
| **H10** | A locked session keeps its slot and room | Fix `start[s]` and `room[s]` |
| **H11** | Aggregate demand stays within room capacity | Cumulative per room type |
| **H12** | A promotion and its subgroups are never busy together | NoOverlap over the whole hierarchy |

### Domain reduction before search

**H4, H5, H6, H8, H9 and H10 are applied by reducing variable domains before the search begins**, not
by posting constraints checked afterwards. This costs nothing during solving and shrinks the space to
explore.

### H12 — why it is not just H2 repeated

In the LMD organisation a **CM gathers the whole promotion** while TD and TP concern its groups and
subgroups. Placing a lecture occupies every student of every subgroup. H12 is the hierarchy-aware
equivalent of the conflict constraint in the curriculum-based formulation of ITC-2007.

### ⚠️ Redundancy, and why it damages the diagnosis run

Two pairs overlap:

- **H2 is subsumed by H12** for any group inside a hierarchy — NoOverlap over the whole
  promotion→group→subgroup chain already forbids what H2 forbids.
- **H11 is implied by H3** once `room[s]` is assigned, and it duplicates pre-analysis check #2 in
  arithmetic form.

Neither hurts feasibility. Both hurt the **diagnosis run**, whose entire value is naming the rule the
user must change. If two assumption literals cover overlapping ground, the solver may return either,
and the report names a rule the user cannot act on.

**The constraint → assumption-literal mapping must be 1:1 and non-redundant.** Which of H2 and H11 are
posted as propagation aids *without* their own literal is **C-6**, unresolved. Decide it explicitly
before building the diagnosis run.

---

## Institutional rules are not constraints

Closed half-days and the shortened-day window do **not** appear above, deliberately. They are
configuration:

- A closed half-day sets `Slot.is_open = 0`; **H9 then does the work**. No new rule.
- A shortened-day window shifts displayed start and end hours. **The slot index does not change**, so
  no variable and no constraint is affected.

Reference configuration: 6 days × 5 periods = 30 slots; the two Saturday afternoon periods closed;
Friday afternoon open; Ramadan window 18 February – 19 March 2026 with a 60-minute shift. **28 of 30
slots open.** Changing any of these changes the timetable produced with no code modification — this is
an acceptance criterion.

See ADR-003, including the condition for promoting such a rule to a hard constraint.

---

## Objective

```
minimise  Σ ( weight_i × violations_i )
```

| Code | Criterion | Default weight |
|---|---|---|
| S2 | Idle time inside a group's day | 0.25 |
| S3 | Idle time inside a teacher's day | 0.15 |
| S4 | Number of distinct days of presence | 0.10 |
| S5 | Preferred windows declared by a teacher | 0.20 |
| S6 | Rooms markedly under-used or over-used | 0.10 |
| S7 | Spread of one course's sessions across the week | 0.10 |
| S10 | Midday break preserved | 0.00 |

Defaults sum to **0.90**. A profile renormalises them to sum to **1** before any score is computed,
which is what makes two runs' scores comparable. **S10 has weight 0**: it is measured and displayed
but does not influence the order.

**`S1`, `S8` and `S9` do not exist.** They were retired during specification revision. Codes are
permanent identifiers — never reuse them.

### ⚠️ The raw values are undefined

`v_i(k)` — the measured violation count for criterion `i` on candidate `k` — **has no formula for any
of the seven criteria.** It feeds the score, the contributions, monotonicity, dominance and the weight
learning. This is the single largest specification gap. Tracked as **C-4**.

S2, S4 and S6 can partly inherit from the ITC-2007 curriculum-based definitions. S3, S5, S7 and S10 are
project-specific with no published definition. **S6 additionally has a dead half**: H5 already makes a
room smaller than its group impossible, so "over-used" must mean utilisation rate rather than
over-capacity — the documents never say.

⚠️ **S5 has no input data at all.** `teacher_availability.csv` carries a boolean `is_available` and all
157 rows are 0 — unavailability declarations, as documented. Nothing in the schema expresses a
*preferred* window, yet S5 carries **weight 0.20, the second highest**. See **C-12**, and note that it
interacts with C-5: a zero-valued S5 makes the teacher-favouring profile differ by S3 alone, so
candidates may converge and the "three candidates" acceptance test fails for an invisible reason.

Implement each criterion through the `Criterion` Protocol, which requires `raw_value` **and** `bounds`
together, deliberately, so a criterion cannot be half-defined (ADR-009).

### Auxiliary variables the objective needs

Idle time per group per day requires the first and last occupied period plus reified gap indicators.
**These are not counted in the model-size table below** — the stated size is an underestimate.
Encoding the objective is the second unknown of this phase, after `y` channelling.

---

## Model size on the reference instance

| Element | Value |
|---|---|
| Sessions to place | 218 |
| Open slots | 28 |
| Integer variables | 436 — `start[s]` and `room[s]` per session |
| Interval variables | 218 |
| Boolean `y[s][t]` | **at most** 6,104, reduced by domain pruning |
| Hard constraint families | 12 |
| Quality criteria | 7, of which 6 with non-zero default weight |
| Objectives | 1 per weight profile |
| Solves per run | 3, one per profile, sequential |
| Candidates retained | at most 3, duplicates removed |

⚠️ **"At most 3, duplicates removed" conflicts with the acceptance criterion "at least three candidates
produced."** If two profiles converge, the system behaves correctly and the test fails. Tracked as
**C-5**.

---

## Weight profiles and the portfolio

Three profiles by default: **balanced** (catalogue values), **student-favouring** (raises S2),
**teacher-favouring** (raises S3 and S5). The total budget is divided between them; a candidate
identical to one already obtained is not retained.

Diversity comes from **varying the objective, not the random seed** — deliberately. Two candidates
differing only by seed differ for no reason anyone can state; two candidates from two profiles differ
for a reason that is *exactly* the difference between those profiles. That is what makes the comparison
screen meaningful.

---

## Solver configuration

| Parameter | Value | Why |
|---|---|---|
| Time bound | `max_deterministic_time` | Reproducibility. **Not** `max_time_in_seconds` — parallel workers race under a wall clock, and a fixed seed does not fix it (ADR-011) |
| Wall-clock ceiling | safety net only | Prevents a hang. Reaching it is an anomaly to log, not a normal exit |
| Workers (stage 2) | all available | |
| Workers (stage 3) | **1** | Imposed: solving under assumptions does not admit parallelism |
| Objective (stage 3) | **none** | Imposed: with an objective the solver returns the whole assumption set |
| Seed | recorded with the run | Reproducibility is an acceptance criterion |

⚠️ The deterministic-time → wall-clock ratio is **machine-dependent and must be calibrated on the
reference instance**. Until it is, the user-facing time limit is an unvalidated guess. See
`docs/status.md`.

---

## Examination model — increment 2

| Code | Statement | Construction |
|---|---|---|
| **X1** | A student never has two examinations in one slot | NoOverlap on each student's intervals |
| **X2** | Assigned room capacity covers the candidate count | Sum of assigned capacities |
| **X3** | Examination inside the session period, outside holidays | Domain restriction on the start variable |
| **X4** | A supervisor is not assigned two examinations in one slot | NoOverlap on each supervisor's intervals |
| **SX1** | Examinations of one group spread over the session *(soft)* | Penalty on proximity |

Three differences from the weekly model:

1. **An examination may occupy several rooms at once.** Room assignment becomes a boolean matrix with a
   capacity sum, **not** a single integer `room[s]`. SRS §6.8 calls this "the same construction with
   different variables"; it is not — the variable schema differs structurally. **Do not bake a
   single-room abstraction into shared solver code.** (R-6.)
2. The horizon is the examination period, not the week, so the slot index is computed over that
   period's days.
3. **Conflicts are computed per individual student, not per group.** For the weekly timetable a
   promotion follows a fixed programme so reasoning on groups loses nothing; for examinations two
   students of one group may sit different optional courses. The 425-student file exists for this and
   only this.

X1–X4 and SX1 are **not** among the 19 constraints of the catalogue (12 hard + 7 soft).
