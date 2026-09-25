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
size (for reports): `size(root) × Π (size(child)/size(parent))` along the chosen children.
The solver merges atoms whose session sets are identical into one constraint set and counts
the merged atom's objective terms once per atom it stands for.

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
restriction, not a rule: manual placement may use any compatible room, and in a repair every
compatible room the reference timetable uses stays available to all occurrences of that
activity.

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

Symmetry: occurrences of one activity share groups, instructors, duration and domain, so the
solver orders them (`present` non-increasing, `start` increasing among present ones). Pinned
and fixed occurrences, and every occurrence of an activity named in a `precedence` or
`consecutive` rule (those pair occurrence k with occurrence k), are left out of the ordering.
Metrics that compare solutions per session (stability, diffs) are computed per activity on
multisets of placements, so the ordering never changes a reported value.

## 4. Configurable rules

Each rule instance has a scope (targets), parameters, enforcement `hard` or `soft`, and when
soft a tier and integer weight. "Resources" are instructors or student groups (a group
resource is enforced on each of its atoms). Violation units are what the soft penalty counts.

| Code | Scope | Parameters | Meaning | Violation unit |
|---|---|---|---|---|
| `max_periods_per_day` | resources | `limit` | Occupied periods per day ≤ limit | periods above limit, per day |
| `max_consecutive_periods` | resources | `limit` | No run of more than `limit` occupied periods; a run ends at a free period or a non-joinable boundary | periods above limit, per run |
| `max_days_per_week` | resources | `limit` | Days with any session ≤ limit | days above limit |
| `break_in_window` | resources | `periods`, `min_free` | Each day, at least `min_free` of the window's periods are free | missing free periods, per day |
| `avoid_slots` | resources or activities | `slots` | No session occupies the slots | occupied periods in the slots |
| `earliest_start` | resources or activities | `period` | No session before this period | occupied periods before |
| `latest_end` | resources or activities | `period` | No session after this period | occupied periods after |
| `min_days_between` | activities | `days` | Occurrences of the activity at least `days` apart | occurrence pairs too close |
| `not_overlapping` | activities (≥2) | – | Listed activities never overlap in time | overlapping periods |
| `same_start` | activities (≥2, equal sessions per week) | – | Each other activity's occurrences start at the same slots as the first activity's (compared as multisets) | per other activity: min(placed occurrences of the two) − matching starts |
| `same_day` | activities (≥2) | – | Each other activity's occurrences fall on the same days as the first activity's (multisets) | per other activity: min(placed occurrences of the two) − matching days |
| `different_days` | activities (≥2) | – | No two listed activities on the same day | per day: listed activities present beyond the first |
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
| `student_idle` | Σ over atoms, days: free open slots strictly between the first and last occupied slot (idle periods; every kind of student counts once, whatever its size) | 2 |
| `instructor_idle` | Same per instructor (periods) | 2 |
| `instructor_undesirable` | Occupied instructor periods marked undesirable | 1 |
| `instructor_preferred` | Occupied instructor periods outside the preferred slots, for instructors who declared any | 3 |
| `undesirable_slots` | Σ over occupied (session, slot): slot penalty level (weighted periods) | 2 |
| `room_fit` | Σ L_s × (capacity − need_s) (empty seat-periods) | 3 |
| `room_preferences` | Sessions outside preferred rooms (activities with preferences) + sessions in avoided rooms | 3 |
| `room_stability` | Σ over activities: distinct rooms used − 1 | 3 |
| `start_consistency` | Σ over activities: distinct periods of day used − 1 | 3 |
| `instructor_days` | Σ over instructors: max(0, days used − ⌈load / \|P\|⌉) | 2 |
| `stability` | Per activity: occurrences whose slot is not in the reference multiset + occurrences whose room is not in the reference multiset; only with a reference solution | 1 in repair profiles |

### Exact auxiliary variables

Every auxiliary variable is defined in both directions, never only bounded from the side the
objective pushes it. A solution that is feasible but not optimal therefore reports its true
objective values, and the bound a finished tier leaves behind (`tier ≤ value`) constrains the
true value, not an overestimate. Property tests fix random timetables in the model and check
that the minimum and the maximum of every tier coincide with the evaluator's value.

| Quantity | Encoding |
|---|---|
| Disjunction `f = ∨ l_i` (day used, room or period used, activity present on a day) | `l_i ⇒ f` for each i; `f ⇒ ∨ l_i` |
| Conjunction `z = a ∧ b` of 0/1 expressions | `z ≤ a`, `z ≤ b`, `z ≥ a + b − 1` |
| Excess `e = max(0, Σ − limit)` (soft caps, extra days, overlaps) | `e = max(0, Σ − limit)` (linear max) |
| Capped count `k = min(c, Σ)` (stability, alignment) | `k = min(c, Σ)` (linear min) |
| Idle periods of a resource on a day, over its open slots `u` with `occ[u]` = at-most-one sum of covering literals | `before[u] = before[u−1] ∨ occ[u]`, `after[u] = after[u+1] ∨ occ[u]`, `idle[u] = before[u−1] ∧ after[u+1] ∧ ¬occ[u]` |
| Precedence lateness | `late ⇒ present_a ∧ present_b ∧ start_b ≤ start_a + L_a − 1`; `present_a ∧ present_b ∧ ¬late ⇒ start_b ≥ start_a + L_a` |
| Consecutive miss | `(present_a ∧ present_b) − Σ_t (x[a,t] ∧ x[b,t+L_a])`, same day |
| Occurrences too close | Σ_d `on_day(s₁, d) ∧ (Σ over starts of s₂ within the gap of d)` |
| Campus transition | `in(s,t,c) = x[s,t] ∧ Σ_{r∈c} y[s,r]`; `at(u,c) = Σ in(s,t,c)` over covering starts; per boundary and campus pair too far apart: `at(u,a) ∧ at(u+1,b)` |

## 6. Solving procedure

1. **Compile** the snapshot into the problem model: atoms, domains, rule instances.
2. **Pre-check** (§7). Errors are reported; the solve still runs, because elastic placement
   produces the best partial timetable and per-session explanations.
3. **Warm start**: a constructive heuristic keeps every pinned placement and, in a repair,
   every reference placement that is still valid; it then places the other sessions in order
   of tightest domain, each at the first start and smallest room that clash with nothing
   placed so far. The result is the hint.
4. **Tier 0**: minimize unscheduled periods. If sessions stay unscheduled and their
   activities had rooms skipped as far too large (§2), those activities get every compatible
   room and tier 0 is solved again from the incumbent (a large room beats no room).
5. **For each selected profile**, tiers 1…k in order: minimize the tier's weighted sum subject
   to every earlier tier ≤ its best value; hint the incumbent.
6. **Validate** each result with the evaluator; compare the solver's tier values with the
   evaluator's; store the candidate with its metrics.
7. **Explain** every unscheduled session (§8).

Time budget: tier 0 may use 30 % of the run's budget. What is left is shared evenly by the
profiles still to solve, and inside a profile by its non-empty tiers still to solve, so time
left over by a tier proven optimal passes to the next. Every solve gets at least half a
second. Reproducible mode limits and counts deterministic time, so the budget is divided the
same way on every machine; fastest mode uses wall-clock time (ADR 0018).

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

## 8. Explanations, suggestions and diagnosis

**Suggestions.** For a session `s` and a target (slot `t`, room `r`), the evaluator lists
every reason the placement is invalid given the other assignments: slot closed or out of
domain (which rule), instructor busy (with which session), student atom busy (which group,
which session), room occupied or unavailable, room incompatible (type, features, capacity),
hard rule violated. For valid targets it reports the change of every objective. Suggestions
rank all valid targets by the lexicographic objective change and show the best invalid ones
with their blocking sessions.

**Explanation of an unscheduled session** (`evaluation.explain`, evaluator only). Every start
window the session could physically use (it fits in the day without running across a break)
is checked with the rest of the timetable in place. A window is ruled out by time
requirements (closed slot, unavailability of an instructor, students or the activity, a hard
slot rule, a fixed time), by people (the instructor or the students have another session, an
occurrence is already on that day, a hard rule would break) or, when none of those apply, by
rooms (every suitable room is taken or closed). The explanation counts the windows each
obstacle rules out, names the sessions involved, lists places where the session fits now if
any, and, when no room suits the session at all, counts the rooms failing each requirement.
Invariant, checked by property tests: when tier 0 is proven optimal, no unscheduled session
fits anywhere with the rest of the timetable in place.

**Relaxation diagnosis** (`solver.relaxation`). For an incomplete result, a relaxation run
places every session it can while pricing the data changes it relies on:

| Relaxation | Cost |
|---|---|
| Open a closed slot | 50 per period |
| Instructor, student group or activity available at a slot it is not | 10 per period |
| Hard avoid / earliest-start / latest-end rule allowing a slot | 10 per period |
| Fixed occurrence placed elsewhere (time or room) | 30 |
| Room of another type, lacking a feature, outside the required campus or building, or outside the allowed list | 20 each |
| Room with too few seats | 5 per missing seat |
| Room more than `ratio ×` the seats needed (skipped by the search) | 1 |
| Extra occurrence of a different-days activity on a day | 10 |
| Any other hard rule | 10 per violation unit |

Physics is never relaxed: conflicts, room double-booking, room closures, the length of the
day and breaks. Rooms less than half the size needed are not considered, and each session
keeps its fifteen cheapest incompatible rooms. The run first minimizes unscheduled periods
(what no relaxation fixes: an instructor or group with more teaching than time), then the
total relaxation cost. The result lists each change with its cost, the sessions relying on
it, the slots concerned and an English sentence; interfaces build localized text from the
structured fields. Property tests check that the changes are exactly the requirements the
evaluator finds broken in the relaxed timetable, that physics is never broken and that the
costs add up to the optimized total.

## 9. Repair

Repair is a run with a reference solution (normally the current draft), `stability` in tier 1
and the warm start of §6, and optionally a scope that pins every session outside a chosen set
(for example, only sessions affected by a closed room may move). A pin keeps a session's
start (and room, when given) but not its presence: if a pinned placement cannot coexist with
the rest, the session is reported unscheduled rather than making the run infeasible. A pin
that is no longer valid on its own (its start or room left the domain) stops the run with an
explanation before solving.
