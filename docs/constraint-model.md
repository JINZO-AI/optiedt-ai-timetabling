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

The effective count is well below 6,104 because H4–H10 prune domains before search. 6,104 is recorded
as an upper bound, never as an estimate. **Measured: 5,328** (`solver/occupancy.py`, 2026-07-30).

### The channelling constraint — C-7, resolved 2026-07-30

The rule linking `start[s]` to `y[s][t]` appears in none of the three PDFs. It is written here. For
each session `s` of duration `d` with pruned start domain `D(s)`:

```
x[s,t₀] ∈ {0,1}                        for every t₀ ∈ D(s)      "s starts at t₀"
exactly_one( x[s,t₀] : t₀ ∈ D(s) )                              s starts somewhere
start[s] == Σ t₀ · x[s,t₀]                                      channel to the integer
y[s,t]  == Σ { x[s,t₀] : t₀ ∈ D(s), t₀ ≤ t ≤ t₀+d−1 }           "s occupies t"
```

The last line is the answer, and it is uniform in `d`: a 1-period session's `y[s,t]` collapses to
`x[s,t]`, a 2-period session's is `x[s,t−1] + x[s,t]`. `exactly_one` makes at most one term of any such
sum true, so the sum is always 0 or 1 and the equality is exact — no inequality pair, no big-M.

`y[s,t]` is created only for slots some valid start can reach; the rest are constant 0 and are omitted
rather than posted. That omission is the pruning referred to above.

⚠️ **Built on demand, not on every solve.** `build_occupancy()` adds 10,048 variables and, measured
across three seeds on the reference instance, takes the feasibility solve from **2.9–4.1 s to
7.6–8.0 s** (deterministic time 0.4–1.9 → ~6.1). The Phase 2 feasibility solve therefore does not call
it. Nothing here may narrow a domain or forbid a placement: every constraint it posts is a consequence
of `start[s]`, so any solution of the model without it extends to exactly one solution with it. If that
ever stops being true, a soft criterion has silently become a hard one.

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
| **H11** | Aggregate demand stays within room capacity | Implied by H3 once a room is assigned — no separate posting |
| **H12** | A group and every ancestor in its hierarchy are never busy together | Per group: NoOverlap over that group's own sessions plus every ancestor's — never a flat whole-hierarchy grouping (see below) |

### Domain reduction before search

**H4, H5, H6, H8, H9 and H10 are applied by reducing variable domains before the search begins**, not
by posting constraints checked afterwards. This costs nothing during solving and shrinks the space to
explore.

### H12 — why it is not just H2 repeated, and why it is not a flat promotion-wide grouping either

In the LMD organisation a **CM gathers the whole promotion** while TD and TP concern its groups and
subgroups. Placing a lecture occupies every student of every subgroup. H12 is the hierarchy-aware
equivalent of the conflict constraint in the curriculum-based formulation of ITC-2007.

⚠️ **A first implementation grouped every session under a promotion into one `NoOverlap` set — this is
wrong, and was caught and fixed on 2026-07-30 (`docs/status.md`).** It forces unrelated siblings (e.g.
two different TP subgroups of two different TD groups) to never run in parallel, even though they are
disjoint sets of students who obviously can. The reference instance is genuinely infeasible under that
reading in under a tenth of a second — the exact signature described below in "Redundancy" territory,
except this was a correctness bug, not a redundancy.

The correct relation, matching `constraint_catalogue.csv`'s own description of H12 ("Parent busy =>
children busy (and vice-versa)"), is **ancestor-or-self**: two sessions conflict iff one's group is an
ancestor of the other's, or they are the same group — never for sharing a distant common ancestor like
the promotion. Implemented per group: gather that group's own sessions plus every ancestor's, and
`NoOverlap` that set. Because a group's own chain always starts with itself, this still forces
same-group exclusivity, which is why H2 remains fully subsumed (see below) even after the correction.

### ⚠️ Redundancy, and why it would damage the diagnosis run

Two pairs overlap:

- **H2 is subsumed by H12** for any group inside a hierarchy — the ancestor-or-self `NoOverlap`
  described above already forbids what H2 forbids, since it includes a group's own sessions.
- **H11 is implied by H3** once `room[s]` is assigned, and it duplicates pre-analysis check #2 in
  arithmetic form.

Neither hurts feasibility. Both would hurt the **diagnosis run**, whose entire value is naming the rule
the user must change. If two assumption literals covered overlapping ground, the solver could return
either, and the report would name a rule the user cannot act on.

**C-6 — RESOLVED 2026-07-30.** The constraint → assumption-literal mapping is 1:1 and non-redundant by
construction: `carries_assumption_literal` is `True` only for **H1, H3, H7 and H12** — the four
constraints that are real CP-SAT postings a literal could attach to. H2 and H11 are registered as
documented no-ops (`solver/constraints/noop.py`) with `carries_assumption_literal = False`, since there
is no separate posting to attach a literal to. H4, H5, H6, H8, H9 and H10 are likewise `False` — they
are domain restrictions applied at variable construction (`solver/variables.py`), never posted as
constraints at all.

⚠️ **H1, H3, H7 and H12 being correct does not mean a solution exists.** For three sessions this
section warned instead that full room interchangeability at high occupancy "makes room assignment a
hard symmetric search". It does not — on this instance the same encoding, with the same fully
interchangeable rooms, solves in ~3 s. What was actually happening is that the instance had **no
solution**, and CP-SAT was being asked to prove an infeasibility its propagators cannot construct:
`AddCumulative` reasons about area (160 period-units against 168 available, which fits) and cannot see
that a 5-period day will not tile with 2-period sessions. Posed as counting rather than as intervals,
the same question returns `INFEASIBLE` in 0.088 s.

**The rule to take from it:** when a solve returns `UNKNOWN`, establish that a solution exists before
treating it as a performance problem. An instant `INFEASIBLE` is evidence of a too-tight model; its
absence is *not* evidence of a sound instance. See **C-13** in `docs/open-questions.md`.

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

### The raw values — RESOLVED 2026-07-30, formulas in `docs/open-questions.md`

`v_i(k)` — the measured violation count for criterion `i` on candidate `k` — now has a formula for
every one of the seven criteria, implemented in `optiedt.analysis.criteria` (post-hoc, against a
realized `Candidate`) and independently in `optiedt.solver.objective` (as CP-SAT expressions over
decision variables — the two layers may not share this code; see that module's docstring for why).
**Full formulas, bounds and the reasoning behind each choice are in `docs/open-questions.md`, C-4** —
this section only summarises what changed.

S2 does inherit from ITC-2007's idle-time definition, applied per **leaf group** (a TP subgroup, via its
ancestor-or-self chain) rather than per hierarchy level, so a gap is not counted three times. S4 and S6
do **not** literally inherit their ITC-2007 namesakes despite the note this section used to carry:
ITC-2007's `MinimumWorkingDays` assumes a course repeats within the week for one curriculum, which this
instance's data does not (`occurrences_per_week` is 1 throughout); ITC-2007's `RoomStability` is about a
course reusing rooms, not utilisation rate. S4 uses `ClusterBusyTimesConstraint`'s per-**teacher**
reading instead (a judgment call — leaf group was a defensible alternative); S6 follows the catalogue's
own wording ("under/over-utilised") against a per-room-type target utilisation, resolving the dead half
H5 leaves it (over-capacity is impossible, so "over-used" means booked more intensively than the type's
own average).

⚠️ **S6 can only be optimised by the solver for non-cumulative room types.** For "fully interchangeable"
types (`Variables.cumulative_room_types` — Amphi, Lab_Info, Lab_Sciences, C-13) there is no per-room
decision variable at all; the specific room is chosen by a deterministic post-solve labeller in
`solver/engine.py` that the objective cannot see or influence. `solver/objective.py`'s S6 term therefore
only covers Salle. `analysis/criteria.py` still scores every room correctly after the fact, regardless.

**S5 uses a labeled proxy, not real preference data (C-12).** `teacher_availability.csv` still carries
only unavailability declarations — nothing in the schema expresses a *preferred* window. Rather than
measure S5 as identically zero (the option C-5 warned against), S5 counts sessions placed in the first
or last period of the day: a standard, teacher-agnostic convention, explicitly recorded as a stand-in
for real preference data (option (a) in C-12) rather than a definition of any one teacher's actual
preference. See `docs/open-questions.md` for why the alternative tested first (generalising a teacher's
own declared unavailability across the week) degenerates on this instance's data.

Each criterion is implemented through the `Criterion` Protocol, which requires `raw_value` **and**
`bounds` together, deliberately, so a criterion cannot be half-defined (ADR-009).

### Auxiliary variables the objective needs — built

`solver/objective.py` builds, per (teacher-or-leaf-group, day) pair needed by an active criterion: an
`occ` boolean per period, an `any_occupied` boolean, `first`/`last`/`idle` integers (S2, S3), an
`extra_days` integer (S4, reusing S3's `any_occupied`); per session, an `edge` boolean (S5); per
non-cumulative room, a `deviation` integer (S6); per (leaf group, course, day) triple with ≥2 candidate
sessions, an `excess` integer (S7). S10 needs no new variable — its occupancy sum is already 0/1 by
construction. All of this is built **only** for criteria carrying a non-zero weight in the profile being
solved, so a profile that zeroes a criterion pays nothing for it. The exact count on the reference
instance under the catalogue's default weights has not yet been measured and recorded here.

---

## Model size on the reference instance

| Element | Value |
|---|---|
| Sessions to place | 218 |
| Open slots | 28 |
| Integer variables | 218 — `start[s]` per session. `room[s]` is **not** a variable: room assignment is `assign[s,r]` booleans, or a cumulative bound plus post-hoc labelling for fully interchangeable types (see H3/H7 above) |
| Interval variables | 218 unconditional, plus one optional per `assign[s,r]` pair |
| Boolean `assign[s,r]` | 770 — `Salle` only; the other three types are cumulative-encoded |
| Boolean `x[s,t₀]` start indicators | **4,720** measured — built on demand |
| Boolean `y[s][t]` | **at most** 6,104, reduced by domain pruning to **5,328** measured — built on demand |
| Objective auxiliaries | **unknown, and deliberately not guessed** — they follow from the criterion formulas, which are C-4. Order of magnitude for planning only: ~612 integers for first/last per group-day, ~1,530 booleans for a gap indicator per group-day-period |
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
