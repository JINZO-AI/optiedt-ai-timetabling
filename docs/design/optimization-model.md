# Optimization model

This is the reference for what the solver optimizes and what the evaluator checks. The solver
(`optiedt.solver`) and the evaluator (`optiedt.evaluation`) implement every definition below
independently (ADR 0009); tests compare them on generated instances.

## 1. Notation

| Symbol | Meaning |
|---|---|
| `D`, `P` | Teaching days of the term, periods of the day (ordered) |
| `u = (d, p)` | A slot; slot index `d·|P| + p` |
| `open(u)` | Slot is open (not closed by the term) |
| `joins(p)` | A session may continue from period `p` into `p+1` |
| `s`, `a(s)` | A session and its activity |
| `L_s` | Duration of `s` in periods |
| `I_s`, `G_s` | Instructors and student groups of `s` |
| `A_s` | Conflict atoms of `s` (ADR 0011): atoms of every group in `G_s` |
| `need_s` | Required seats: the activity's minimum capacity, default Σ group sizes |
| `cover(s, t)` | Slots occupied when `s` starts at `t`: `t, t+1, …, t+L_s−1` |

### Conflict atoms

For each group, its atoms are the combinations of one child per partition at every level
below it; a leaf is its own single atom. Group `g`'s atom set is the union over its
descendants. Two sessions conflict on students iff their atom sets intersect. Estimated atom
size: `size(root) × Π (size(child)/size(parent))` along the chosen children, rounded, min 1.
Atoms whose session sets are identical are merged (sizes added).

## 2. Domains

**Start domain `T(s)`** — slots `t = (d, p)` such that, for every `k < L_s`:

1. `(d, p+k)` exists and is open;
2. `joins(p+k)` holds for every `k < L_s − 1` (no running across a break);
3. no instructor of `I_s`, no atom of `A_s` (via its groups) and not the activity itself is
   `unavailable` at `(d, p+k)`;
4. no **hard** avoid-period, earliest-start or latest-end rule targeting `s`'s resources
   forbids `(d, p+k)`;
5. if the occurrence has a fixed placement, `t` equals it.

**Room domain `R(s)`** — for in-person sessions: active rooms whose type equals the
required type (if any), whose features include the required features, whose capacity is at
least `need_s`, within the campus/building restriction and the allowed-room list, and equal
to the fixed room if any. The solver additionally skips rooms more than `ratio × need_s`
seats (term setting, default 4; ignored when it would empty the domain). This is a search
restriction, not a rule: manual placement may use any compatible room.

## 3. Variables and structural constraints

```
x[s,t] ∈ {0,1}      t ∈ T(s)                 s starts at t
y[s,r] ∈ {0,1}      r ∈ R(s)                 s is in room r
present[s] = Σ_t x[s,t] ≤ 1
Σ_r y[s,r] = present[s]                      in-person sessions only
start[s] = Σ_t t·x[s,t]                      enforced when present
```

| # | Requirement | Encoding |
|---|---|---|
| S1 | Each session placed at most once; unplaced sessions are tier 0 | `present[s]`, objective tier 0 = Σ L_s·(1 − present[s]) |
| S2 | Instructor never in two places | ∀ instructor `i`, slot `u`: at-most-one of `{x[s,t] : i ∈ I_s, u ∈ cover(s,t)}` |
| S3 | Students never in two places | ∀ atom `α`, slot `u`: at-most-one of `{x[s,t] : α ∈ A_s, u ∈ cover(s,t)}` |
| S4 | Room never double-booked, respects unavailability | ∀ room `r`: `NoOverlap({interval(start[s], L_s) present iff y[s,r]} ∪ fixed blockers of r)` |
| S5 | Occurrences on different days (when required) | ∀ activity, day `d`: Σ_{s∈a, t∈d} x[s,t] ≤ 1 |
| S6 | Domains (§2) | Variables are created only for feasible values |

Symmetry: non-fixed occurrences of one activity are interchangeable, so the solver orders them
(`present` non-increasing, `start` increasing among present ones). Metrics that compare
solutions per session (stability, diffs) are computed per activity on multisets of
placements, so this ordering never changes a reported value.

## 4. Configurable rules

Each rule instance has a scope (targets), parameters, enforcement `hard` or `soft`, and when
soft a tier and integer weight. "Resources" are instructors or student groups (a group
resource is enforced on each of its atoms). Violation units are what the soft penalty counts.

| Code | Scope | Parameters | Meaning | Violation unit |
|---|---|---|---|---|
| `max_periods_per_day` | resources | `limit` | Occupied periods per day ≤ limit | periods above limit, per day |
| `max_consecutive_periods` | resources | `limit` | No run of more than `limit` occupied periods; a run ends at a free period or a non-joinable boundary | periods above limit, per window |
| `max_days_per_week` | resources | `limit` | Days with any session ≤ limit | days above limit |
| `break_in_window` | resources | `periods`, `min_free` | Each day, at least `min_free` of the window's periods are free | missing free periods, per day |
| `avoid_slots` | resources or activities | `slots` | No session occupies the slots | occupied periods in the slots |
| `earliest_start` | resources or activities | `period` | No session before this period | occupied periods before |
| `latest_end` | resources or activities | `period` | No session after this period | occupied periods after |
| `min_days_between` | activities | `days` | Occurrences of the activity at least `days` apart | occurrence pairs too close |
| `not_overlapping` | activities (≥2) | – | Listed activities never overlap in time | overlapping periods |
| `same_start` | activities (≥2, equal sessions per week) | – | Occurrence k of each starts at the same slot | occurrences not aligned |
| `same_day` | activities (≥2) | – | Occurrence k of each on the same day | occurrences not aligned |
| `different_days` | activities (≥2) | – | No two listed activities on the same day | same-day pairs |
| `precedence` | activities (ordered pair) | – | Occurrence k of the first ends before occurrence k of the second starts (week order) | violated pairs |
| `consecutive` | activities (ordered pair) | – | Occurrence k of the second starts right after the first ends, same day | violated pairs |
| `campus_travel` | resources | – | Sessions in adjacent periods are on campuses whose travel time fits the gap between the periods | violating transitions |

Hard avoid-slot, earliest-start and latest-end rules are applied as domain restrictions;
the others are posted as constraints. Soft rules add
`weight × Σ violation units` to their tier.

## 5. Built-in objectives

| Code | Definition (natural units) | Default tier (Balanced) |
|---|---|---|
| `unscheduled` | Σ L_s over unplaced sessions (periods) | 0 (always first) |
| `student_idle` | Σ over atoms, days: free open slots strictly between the first and last occupied slot, × estimated atom size (student-periods) | 2 |
| `instructor_idle` | Same per instructor (periods) | 2 |
| `instructor_undesirable` | Occupied instructor periods marked undesirable | 1 |
| `instructor_preferred` | Occupied instructor periods outside the preferred slots, for instructors who declared any | 3 |
| `undesirable_slots` | Σ over occupied (session, slot): slot penalty level × `need_s` (student-periods) | 2 |
| `room_fit` | Σ L_s × (capacity − need_s) (empty seat-periods) | 3 |
| `room_preferences` | Sessions outside preferred rooms (activities with preferences) + sessions in avoided rooms | 3 |
| `room_stability` | Σ over activities: distinct rooms used − 1 | 3 |
| `start_consistency` | Σ over activities: distinct periods of day used − 1 | 3 |
| `instructor_days` | Σ over instructors: max(0, days used − ⌈load / \|P\|⌉) | 2 |
| `stability` | Per activity: occurrences whose slot is not in the reference multiset + occurrences whose room is not in the reference multiset; only with a reference solution | 1 in repair profiles |

Idle-period encoding per resource and day: `before[u] ≥ occ[u]`, `before[u] ≥ before[u−1]`,
`after[u] ≥ occ[u]`, `after[u] ≥ after[u+1]`, `idle[u] ≥ before[u−1] + after[u+1] − 1 − occ[u]`
over the day's open slots, where `occ[u]` is the at-most-one sum of covering start literals.
Minimization makes the lower bounds tight.

## 6. Solving procedure

1. **Compile** the snapshot into the problem model: atoms, domains, rule instances.
2. **Pre-check** (§7). Errors are reported; the solve still runs, because elastic placement
   produces the best partial timetable and per-session explanations.
3. **Warm start**: a constructive heuristic places sessions in order of tightest domain,
   choosing the slot and room that minimize immediate conflicts; the result is the hint.
4. **Tier 0**: minimize unscheduled periods.
5. **For each selected profile**, tiers 1…k in order: minimize the tier's weighted sum subject
   to every earlier tier ≤ its best value; hint the incumbent.
6. **Validate** each result with the evaluator; compare the solver's tier values with the
   evaluator's; store the candidate with its metrics.
7. **Explain** every unscheduled session (§8).

Time budget: tier 0 may use up to 40 % of a profile's budget; the remainder is split evenly
over the profile's non-empty tiers, and time left over by a tier proven optimal passes to the
next. Reproducible mode uses deterministic time; fastest mode uses wall-clock time (ADR 0018).

## 7. Pre-checks

| Check | Proves infeasibility? | Example message |
|---|---|---|
| Empty start domain | Yes | "ALG201 Lab (G2a): no 2-period window — Dr. Haddad is unavailable in all 14 open windows" |
| Empty room domain | Yes | "No computer lab with ≥ 32 seats and feature *MATLAB*" |
| Instructor load > available periods | Yes | "Dr. Haddad: 16 periods to teach, 12 available" |
| Atom load > available periods | Yes | "L2-CS G3/English: 34 periods required, 30 open" |
| Room-pool demand > supply (per compatible room set, per duration) | Yes | "Computer labs: 88 periods needed, 80 available (8 rooms × 10 open)" |
| Fixed placements colliding | Yes | "Two fixed sessions in Amphi A on Monday P1" |
| Sessions per week > placeable days (different days) | Yes | "MATH101 Tutorial: 3 sessions on different days, only 2 days possible" |
| Hard rule unsatisfiable by load (max days × periods/day < load) | Yes | "Dr. Ben Ali: at most 2 days × 4 periods, needs 10 periods" |
| Utilization above 90 % of a pool | No (warning) | "Lecture halls: 94 % of open periods needed" |

## 8. Explanations and suggestions

For a session `s` and a target (slot `t`, room `r`), the evaluator lists every reason the
placement is invalid given the other assignments: slot closed or out of domain (which rule),
instructor busy (with which session), student atom busy (which group, which session), room
occupied or unavailable, room incompatible (type, features, capacity), hard rule violated.
For valid targets it reports the change of every objective. Suggestions rank all valid
targets by the lexicographic objective change and show the best invalid ones with their
blocking sessions.

For an incomplete result, a **relaxation run** can be requested: selected hard requirements
become elastic with costs (instructor/group unavailability 10 per period, closed slots 50,
room type 20, capacity shortfall 5 per seat, fixed placements 30, hard rules 10 per unit,
different-days 10) and total relaxation cost is minimized with every session placed. The
result lists the data changes that together admit a complete timetable.

## 9. Repair

Repair is a run with a reference solution, `stability` in tier 1, the current draft as hint,
and optionally a scope that fixes every session outside a chosen set (for example, only
sessions affected by a closed room may move).
