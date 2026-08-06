# Session history — archive

**Not a working document.** Read `docs/dashboard.md` for state and `docs/status.md` for detail. This
file exists so the *reasoning* behind past decisions survives, and so a future session can check what
was already tried before repeating it.

Two entries earn re-reading regardless of what you are working on:

- **2026-07-30, fourth continuation** — how a plausible, well-evidenced conclusion (C-13, "the model is
  hard to solve") turned out to be wrong, and the reasoning error that let it stand for three sessions.
- **2026-07-30 (first)** — the H12 bug, and why at high occupancy a too-tight model is indistinguishable
  from an unsolvable instance.

---

## Superseded resume block — 2026-07-30

<details>
<summary>What this file told the previous session to do, and why it was wrong</summary>

> Resume OptiEDT Phase 2. Read `CLAUDE.md`, then `docs/status.md` in full (all "Session log —
> 2026-07-30" entries), then `docs/open-questions.md`'s C-13 — do not open the PDFs.
>
> The loader, variables, all 12 constraint builders (H12 ancestor-lineage fix included), the C-13
> cumulative-constraint reformulation, and a greedy warm-start hint are all committed and green
> (`c1be462`, `480061e`, `8f22e2b`, `c18e963`; 24 tests, ruff, mypy, format, 7/7 import contracts, all
> pass with solver-marked tests excluded from the default fast path). **Do not redo any of this work.**
>
> **Task 11 is still blocked. Three independent, legitimate techniques have now been tried and none
> resolved it, alone or combined:**
>
> | Configuration | Budget | Result |
> |---|---|---|
> | Cumulative reformulation + warm-start hint + tuning | 480s wall | `UNKNOWN`, 435,688 conflicts, 2.35M branches |
> | Cumulative reformulation + tuning, no hint | 480s wall | `UNKNOWN`, 405,301 conflicts, 2.42M branches |
> | Cumulative reformulation + tuning | 180s wall | `UNKNOWN`, 96,020 conflicts, 1.28M branches |
> | Cumulative reformulation, default parameters | 480s wall | `UNKNOWN` (via the integration test's own fixture) |
> | Per-room encoding + tuning (pre-reformulation) | 480s wall | `UNKNOWN`, 29 conflicts, 2.29M branches |
> | Per-room encoding, default parameters | 360s wall | `UNKNOWN`, 337,954 conflicts |
> | Room assignment alone (H3+H7, no teacher/hierarchy), per-room | 200s wall | `UNKNOWN`, 78,824 conflicts |
>
> **The warm-start hint made essentially no difference** (435,688 vs. 405,301 conflicts at the same
> budget, both `UNKNOWN`) despite covering 190/218 sessions - and the greedy that built it couldn't
> reach full coverage either: MRV order alone gets stuck at 26/218; 3,000 random restarts plateau
> around 190/218 (`solver/warm_start.py`, measured 2026-07-30). Three techniques - a cumulative
> reformulation, CP-SAT parameter tuning, and a constructive warm-start - have now converged on the
> same result. This is no longer "try one more lever"; it is a genuinely hard instance for this model
> within the budgets tested so far (up to 480s / 8 minutes).
>
> Two things remain independently confirmed and should not be re-litigated:
>
> - **Pure time scheduling (H1+H12, no rooms at all) is fast** - confirmed `OPTIMAL` before this
>   investigation started. The difficulty is specifically in the room dimension.
> - **No constraint subset, across this entire investigation, has reproduced an instant `INFEASIBLE`.**
>   Every result has been `UNKNOWN` after real search effort, never the sub-0.1s signature the H12 bug
>   produced. This remains evidence of hardness, not of a remaining correctness bug - H1-H12 are
>   believed correct by construction and by extensive independent testing.
>
> **What's left, genuinely untested:**
>
> 1. **A much larger budget** (tens of minutes to hours) - only up to 480s has actually been tried.
> 2. **Symmetry-breaking specifically on `Salle`** (the one remaining per-room type) - considered
>    unlikely to matter (29% occupancy) but never directly isolated.
> 3. **A more sophisticated construction heuristic** for the warm-start (proper backtracking or a
>    matching-based room assignment instead of greedy first-fit) - might close more than the ~87%
>    coverage reached so far, though the fact it barely helped even at that coverage is a discouraging
>    sign for this direction specifically.
> 4. **Reconsidering the model more radically** (e.g. additional redundant/implied constraints to help
>    propagation, or a different global-constraint structure entirely) - a bigger investment than
>    anything tried so far.
>
> **A second, independent finding, still unresolved**: under `num_workers=0` (parallel),
> `max_deterministic_time` does not tightly bound the search the way ADR-011 assumes for a
> single-worker budget - configured limits have consistently been exceeded before the wall-clock
> ceiling actually stops the run. Flagged, not yet calibrated.
>
> **Before running any solve with `num_workers=0`, be aware it will use every CPU core** and can make
> even trivial shell commands stall for tens of seconds to minutes — budget for it, and always track
> background solves explicitly so you can stop them rather than leave them orphaned (see the incident
> in the first 2026-07-30 session log entry below).

**Every "genuinely untested" option listed above is now moot.** None of them was needed: a larger
budget would have searched an empty space for longer, symmetry-breaking would have pruned equivalent
non-solutions, and a better warm-start construction could not have exceeded 202 of 218 because that is
the arithmetic maximum. The one thing never tried was **checking whether a solution existed at all**,
which takes 0.088 s.

</details>

---


---

## Session log — 2026-07-30/31: Phase 3, from two undecided formulas to a closed phase

Phase 3 began blocked on **C-4** (no soft criterion had a defined raw value or bounds) and **C-12**
(S5 carried weight 0.20 and had no input data at all). Both were resolved in `docs/open-questions.md`
*before* any code, per CLAUDE.md — and that order mattered: writing the formulas down first is what
made the S6 scale bug findable later, because there was a stated intention to compare the code against.

**Built:** `analysis/instance_view.py`, `analysis/criteria.py` (the seven criteria),
`analysis/scoring.py`, `analysis/ranking.py` (rank, decompose, dominance, and FR-16's recommendation),
`solver/objective.py` (the same seven formulas as CP-SAT expressions), `recommendations/translator.py`,
`services/portfolio.py`, and `optiedt/validation/itc2007/` (the benchmark harness). Tests went from 27 to 125.

### Five things worth not rediscovering

**S6 was priced 28× too high, and the shapes matched perfectly.** `analysis/criteria.py` measured a sum
of fractions; `solver/objective.py` measured the same quantity in periods. Both were structurally
correct, and reading them side by side showed nothing — the factor was `open_slot_count`. It was caught
only by `tests/integration/test_objective_matches_analysis.py`, which requires the two layers to agree
*numerically* on the same placements. **When one formula is implemented twice on purpose, the guard has
to compare values, not read code.** Fixing it moved S2 19→2, S7 29→14, score 83.6→85.5: the
over-weighting had been consuming search effort belonging to criteria that actually carry weight.

**The warm start was pinning the whole portfolio.** All three weight profiles returned the *same*
timetable at total budgets 15, 45 *and* 90, scoring an identical 78.076 every time. Six times the
budget and three different objectives producing one candidate is not a tuning problem, and it was
misread as one for most of a session. The hint is an attractor the objective cannot pull the search
away from; withholding it under an objective gives three distinct candidates. It is kept for
feasibility-only solves, where it is pure acceleration.

**The "~11× deterministic-time overshoot" never existed.** `max_deterministic_time` binds *exactly*,
per worker; `CpSolver.deterministic_time` reports the **sum across workers**, and ~11 was the worker
count on a 16-core machine. The figure had survived two sessions, including one in which it was
deliberately salvaged from an analysis known to be wrong — see C-13's entry below and the note now
appended to it. **Salvaging a measurement from a refuted analysis is exactly when it is least likely to
be re-derived.**

**C-16 was diagnosed twice, wrongly, before it was diagnosed right.** Reproducibility failed at
production worker counts — three identical requests, three different timetables, every one proving
optimality. First recommendation: fix `workers = 1`. Second: declare it a specification conflict the
supervisor had to resolve. Both wrong, and for one traceable reason: **every configuration compared
had moved two variables at once**, worker count *and* search strategy, so the diversity collapse was
attributed to low parallelism when the warm start was causing it. `interleave_search` makes the
parallel search deterministic; ADR-011 was amended rather than reversed, and the result was *faster*
(306 s → 147–150 s) as well as reproducible. The option that turned out to be half the answer —
"remove the warm start" — had been listed and dismissed as speculative.

**A blocker was asserted that did not exist.** Portfolio orchestration was recorded as blocked on C-5
and belonging to Phase 4–5. `docs/open-questions.md`, the authority, records C-5 against *Phase 6
acceptance*; SRS Table 29 already fixes the implementation behaviour. Nothing was blocked. Same shape
as C-13: a plausible blocker nobody tried to falsify.

### Closing the phase

Six closure items: portfolio orchestration, the portfolio measurement, reproducibility and ADR-011's
overdue calibration, FR-16, a documentation sweep, and validation on the published instances.

**ITC-2007 validation** was built last (2026-07-31) as `optiedt/validation/itc2007/` — a *separate*
model of a *different* problem, deliberately. Forcing ITC-2007 through the reference instance's schema
would have validated an adapter and been reported as validating an engine. The cost function is
transcribed from the archive's own bundled validator and then **checked against seven solutions the
archive ships**, reproducing every published component cost exactly; without that check every figure
the harness prints would be merely self-consistent.

**21 of 21 valid. The cost gap is large — median 1269 % — and saying so plainly is the point.** The
references are metaheuristics tuned for this exact problem, several run without a time limit, against
roughly fifty seconds of exact search; the strategy document says outright that beating them was never
the objective. What keeps that number from being an indictment is separate evidence that the *model* is
right: `comp11` solved to **cost 0, proven optimal**, and `comp01` reached the published optimum of 5
given more search. Without those two, "the gap is search budget, not modelling" would have been a
comfortable assumption rather than a measured one — and this project has already paid three sessions
for one of those. Results in `docs/status.md`.

**And it immediately earned its place.** The harness's own encoding check fired on 2 of the 21
instances. The encoding turned out to be right: under `interleave_search`, `CpSolver.objective_value`
is reported a few units **above** the objective evaluated at the very solution the solver hands back,
on solves that stop before proving optimality — with the parameter off, they agree exactly. Nothing in
the project is affected, and the reason is worth stating plainly: **no score, ranking or display reads
`SolverOutput.cost`**, because `analysis/` may not import `solver/` and must recompute from the
placements. A solver misreporting its own answer is precisely the failure that layer boundary was drawn
to survive, and it survived it without a code change. Recorded in ADR-011.

The audit that closed the phase found **five** live documentation errors, four of the same kind — a fact
corrected in one file and left standing in another:

1. `constraint-model.md` recorded the objective's auxiliary count as unmeasured; `status.md` gave 5,249.
2. `open-questions.md` still carried the refuted deterministic-time claim as open — and had explicitly
   *salvaged* it from the wrong C-13 analysis as the one part worth keeping.
3. `README.md` still said Phase 3 awaited two specification decisions resolved the day before.
4. `status.md`'s portfolio measurement said "✅ target < 5 min met" and "recorded as missed" in the
   same cell.
5. Three documents said `origin/main` was at `0dc0078`. It is at `acf9aa0` — its child. **A repository
   fact that `git rev-parse` answers in a second had been wrong in three places for two sessions.**

The pattern is worth naming: none was a *disagreement about a decision*. Every one was a number or a
state that moved in one file and not in the others. That is what a documentation sweep is for, and it
is why the sweep has to re-derive rather than re-read.

**A second audit pass found five more, and a third found two beyond those** — after the first had
declared itself finished. Between them: an open-questions heading claiming four resolved when seven
were; a **"Current phase"** field naming a phase that had just closed, which is the first thing a cold
session reads and the one `CLAUDE.md` sends it to; the **instance generator**, a stated PPM §10
deliverable recorded in three documents and scheduled in none, sitting inside a section headed
*RESOLVED*; "one of nine acceptance criteria is met" in a roadmap block while the same file's header
said three; "all four properties pass" beside "10 hypothesis properties" in adjacent rows; and a
missing C-10 that no document admitted was never assigned.

**The lesson is about auditing, not about these particular errors.** Each pass fixed what it found and
then looked again — and each time, looking again found more. An audit that runs once reports the errors
it happened to notice; the count only stops falling when a pass comes back empty. **Repeat until a pass
finds nothing.** Two of the three passes here would have signed off a repository that still contradicted
itself.

---

## Session log — 2026-07-30, fifth continuation: C-7 resolved, Phase 2's modelling complete

**Resolved C-7 in `docs/open-questions.md` before writing any code**, per CLAUDE.md. The specification
names `y[s][t]` and attributes H7 to it but never writes the constraint tying it to `start[s]` — and
with 104 of 218 sessions spanning two periods, `y` has to mean *occupies* `t`, not *starts at* `t`.

**The decision: channel through start indicators.** One boolean `x[s,t₀]` per legal start, an
`exactly_one` over them, `start[s] == Σ t₀·x[s,t₀]`, and then `y[s,t] == Σ{x[s,t₀] : t₀ ≤ t ≤ t₀+d−1}`.
That last line is uniform in duration — it collapses to `x[s,t]` for a 1-period session and is
`x[s,t−1] + x[s,t]` for a 2-period one — and because `exactly_one` lets at most one term be true the
sum is always 0 or 1, so the equality is exact rather than a pair of inequalities. Reifying against the
interval instead would avoid `x`, but costs two constraints per pair and propagates worse. `x` is also
the natural variable for S5 and S7, which are properties of where a session *starts*.

**Implemented in a new `solver/occupancy.py`**, deliberately separate from `variables.py`: it is
accounting, not placement, and every constraint it posts is a consequence of `start[s]`, so it cannot
make a feasible model infeasible. Measured **4,720 `x` + 5,328 `y` = 10,048 variables**; `y` at 87.3%
of the 6,104 upper bound `docs/constraint-model.md` records.

**Built on demand, on evidence.** Switching occupancy on takes the feasibility solve from **2.9–4.1 s
to 7.6–8.0 s** (deterministic time 0.4–1.9 → ~6.1) across three seeds at identical settings. The Phase
2 feasibility solve therefore does not build it; `engine.py` will, once there is an objective to read
it. Paying 2.5× for variables no constraint reads would have been a silent regression of the milestone
measured two entries above.

**Tested both halves separately**, because they fail differently. Five structural unit tests (no solve)
pin *which* `(s, t)` pairs exist — including one that fails specifically if `y` were built as "starts
at", which is the C-7 mistake, and one pinning the measured counts so a pruning change shows up as a
number rather than as a slower solve. One solver-marked test then solves the real instance and checks
what those variables are *worth*: `y` matches the placements exactly, `Σₜ y = duration`, and `Σ x = 1`.

**What C-7 does not close, stated rather than papered over.** The original finding also noted that the
objective's auxiliaries (first/last occupied period per group-day, reified gap indicators) are missing
from the model-size table. **They cannot be counted yet** — how many there are follows from the
criterion formulas, and no soft criterion has one. That is C-4, and inventing an answer here would be
exactly the "assumption made in code and never written down" CLAUDE.md warns about. Order-of-magnitude
figures are recorded for planning; the exact count is owed when C-4 is decided.

---

## Session log — 2026-07-30, fourth continuation: C-13 resolved, and it was not what three sessions thought

**Re-derived the instance's arithmetic from the CSVs before touching any code**, on the principle that
the documentation is evidence rather than truth. That took about ten minutes and produced the answer
the previous three sessions had been searching for with the solver.

**The reference instance had no solution.** All 104 laboratory sessions span two periods; a two-period
session must fit inside one day (H8) on open slots (H9); the week's open slots form six contiguous
runs, five of length 5 and one of length 3. A run of length `L` gives one room `floor(L/2)` disjoint
two-period windows, so a room offers **11 a week**, not 28 periods' worth. `Lab_Info` needed 80 and had
6 × 11 = 66; `Lab_Sciences` needed 24 and had 2 × 11 = 22. Pigeonhole, no solver required.

**Confirmed three independent ways.** Hand arithmetic; CP-SAT maximising placements returned exactly
66 of 80 and 22 of 24 — the ceiling reached from below; and the same question posed as *counting*
rather than as intervals returned `INFEASIBLE` in **0.088 s with zero conflicts**, where the interval
formulation ran 480 s to `UNKNOWN`. `AddCumulative` reasons on area (160 ≤ 168, fine) and cannot see
that a 5-period day will not tile with 2-period sessions. Real capacity was 132 period-units: the
instance was **121 % subscribed**, not 95.2 %.

**H1–H12 were correct all along, and are now demonstrated so positively.** With capacity repaired and
nothing else changed — same encoding, same fully-interchangeable rooms, same parameters — the model
solves in **~3 s**. Four repairs were built and each solved end-to-end with every hard constraint
re-checked from raw data; the one chosen re-types three classrooms as laboratories (`Salle` 10 → 7,
`Lab_Info` 6 → 8, `Lab_Sciences` 2 → 3), keeping the **total room count at 20** and leaving the
calendar, the slot grid and the 32 / 82 / 104 session split untouched. `Salle` sat at 29.3 % while the
laboratories were over-subscribed, so re-typing corrects the actual error instead of padding around it.

**Three previous conclusions are disproved, and the reasoning error behind them is worth naming.** The
investigation had settled on "no constraint subset ever reproduced an instant `INFEASIBLE`, therefore
this is hardness rather than a correctness bug." An instant `INFEASIBLE` *is* evidence of a too-tight
model — but its absence is not evidence of a sound instance, and treating it that way turned an
untested assumption into a conclusion. The sub-0.1 s `INFEASIBLE` existed the whole time; it appears as
soon as the question is asked as counting instead of as intervals. The warm-start's 192/218 plateau was
likewise read as "close to capacity" when at most 202 sessions could be placed at all — it had been reporting the
infeasibility, not struggling with it.

**Fixed the check that should have caught this.** Verification 2 computed `capacity = rooms ×
open_slots` and compared period totals — necessary but not sufficient, and it passed a genuinely
infeasible instance while printing a reassuring 95.2 %. `data/verification/verify_instance.py` now
applies a contiguity bound as well (`sessions of duration d ≤ rooms × Σ floor(L/d)`), verified to fire
on the original mix (short by 14 and by 2) and to pass on the repaired one. It reports `Lab_Info` at
**90.9 % of its two-period windows** — still the binding resource, now measured against a denominator
that means something. ⚠️ **The FR-12 in-application port must carry this bound**, or the same blind
spot ships inside the product.

Full validation green: 7/7 import contracts, ruff, format, mypy on 31 files, **27/27 tests** including
the three solver-marked ones, instance verification, frontend typecheck.

**Then attacked the above rather than defending it**, since the failure mode this session corrected was
precisely a plausible conclusion nobody tried to break. Six falsification attempts, all of which failed
to overturn it:

| Attack | Result |
|---|---|
| Derive the 11-windows-per-room figure by brute force instead of by the `floor(L/2)` formula | 2+2+2+2+2+1 = **11**. Confirmed |
| Reconstruct the original room mix in memory and let CP-SAT search the **full** original model hard for a solution — one feasible answer refutes everything | `UNKNOWN` after 90 s, 124,201 conflicts. No counter-example |
| Repaired instance across seven seeds on production defaults — one failure means 2.9 s was luck | **7/7 placed 218/218**, wall 2.84–3.30 s |
| Does the post-hoc room labeller ever fail? It raises rather than mislabelling | Never raised, across all seven seeds |
| Did removing three `Salle` rooms create a new bottleneck the aggregate hides? Check each capacity-restricted subset | No. Only capacity-30 rooms were removed, so the demanding `>= 35` subset is **unchanged** at 5 rooms / 7.1%; the worst subset is 41.8% |
| Do the re-typed laboratories still satisfy H5? | `Lab_Info` group sizes 10–18 against capacity 20; `Lab_Sciences` 11–15 against 24. OK |

**Two of this session's own claims were wrong and are corrected**, found by that pass rather than by
review: "202 is the true maximum" was an *upper bound* stated as an attained value (whether 202 is
reachable was never tested and does not matter to the argument), and the headline "deterministic time
0.42" came from a diagnostic configuration — `num_workers=8`, warm start off — not from the production
default path, which measures **0.13–0.21**. Both fixed here and in `docs/open-questions.md`.

---

## Session log — 2026-07-30

**Built the full H1-H12 pipeline**, in order: `Instance` aggregate + CSV loader (`optiedt.instance`,
a new package - domain/ must stay pure and preanalysis can't import solver/, so the loader needed its
own leaf package, with a matching `.importlinter` contract), the CP-SAT variables (`solver/variables.py`
- room assignment uses `assign[s,r]` booleans with optional intervals, not a plain `room[s]` IntVar,
because `room[s]` is a decision the solver makes, not a fixed attribute the way `teacher_id` is), and
all 12 constraint codes registered (H1/H3/H7/H12 as real postings, the other eight as documented
no-ops - domain-pruning ones because CP-SAT domain restriction can only happen at variable
construction, subsumption ones because H12/H3 already forbid what H2/H11 would separately forbid).

**C-6 resolved and implemented, not just decided**: `carries_assumption_literal` is `True` only for
H1, H3, H7, H12 - the four constraints that are actually posted objects a literal could attach to.

**Caught a real modelling bug before it went any further.** The first `H12` implementation grouped
every session under a promotion into one `NoOverlap` set. That also forces unrelated siblings - e.g.
two different TP subgroups of two different TD groups - to never run in parallel, which is wrong: they
are disjoint sets of students who obviously can be scheduled at the same time. Solving the real
instance with just this constraint returned `INFEASIBLE` in under a tenth of a second, which is exactly
the signature the project's own docs warn about: at this occupancy, a modelling bug looks identical to
a genuinely unsolvable instance. Isolated it by solving progressively larger subsets of the constraints
against the real data (not a synthetic fixture) until the exact culprit was found.

**The fix**: two sessions conflict under H12 iff one's group is an ancestor of the other's group, or
they're the same group (matching `constraint_catalogue.csv`'s own description, "Parent busy => children
busy (and vice-versa)") - never for sharing a distant common ancestor like the promotion. Implemented
per group: gather a group's own sessions plus every ancestor's, `NoOverlap` that set. Verified correct
in isolation and combined with H1 (`OPTIMAL` both times). **Combined with all four real constraints
(H1+H3+H7+H12) through the actual engine, with all CPU cores and a 60-second deterministic budget, the
solve had not returned when the session was stopped** - so whether the corrected model is fully
feasible on this instance is still an open question, not a settled one.

**Incident: an abandoned background process.** An early debugging run (testing 8 constraint
combinations against the *original, buggy* H12) got backgrounded, and was never explicitly stopped
before moving on to a tighter retest. It kept running in the background - using the old buggy code -
for the rest of the session, consuming enough CPU to make unrelated shell commands (`echo`, `sleep 1`,
even `true`) stall for 20-120 seconds, which looked like a broken tool environment but was actually
resource contention from a forgotten process. Found via `tasklist`/`Get-CimInstance`, confirmed via its
exact command line before touching anything, and killed. **Lesson for next time: track every backgrounded
solve explicitly and stop it before starting a replacement, especially with `num_workers=0`.**

---

## Session log — 2026-07-30, continued: task 11

Picked up per the resume prompt: read and re-verified the H12 fix and `engine.py`, ran
`scripts/run-checks.ps1` (one `ruff format` fix needed on `engine.py`, then all green — 7/7 import
contracts, ruff, mypy on 30 files, 23/23 tests, instance verification, frontend typecheck), and
committed both as `c1be462`.

**Wrote the integration test** (`backend/tests/integration/test_h1_h12.py`) to solve the real instance
end-to-end and then independently recompute H1, H3, H4/H5, H6, H8, H9 and H12 directly from the raw
CSVs and the returned placements - not trusting CP-SAT's status alone, matching the project's own
lesson from the H12 bug that a wrong model can look identical to an unsolvable instance in either
direction. H2 and H11 are not checked separately: they're implied by the H12 and H3 checks
respectively, per C-6.

**Ran it against the real instance and it does not resolve** - see the measurements and root-cause
analysis in "Resume from here" above. Tried three configurations, from a plain 360s run to an 480s run
with `use_probing_search` and `keep_symmetry_in_presolve` enabled; all three returned `UNKNOWN`, never
`INFEASIBLE`. Isolated the room-type structure directly (no solver call): confirmed `Lab_Info` and
`Lab_Sciences` are fully interchangeable room types (every session gets every room of that type as a
candidate) sitting at 95.2% and 85.7% occupancy respectively - the textbook hard case for CP-SAT's
default search. Also checked the group hierarchy depth distribution (6 roots, 15 depth-1, 30 depth-2,
matching the known 6/15/30 split) to rule out a hierarchy-construction bug inflating H12's NoOverlap
sets - it's clean, three levels deep as expected, so H12 is not implicated in the difficulty.

**Conclusion: no modelling bug found.** Every constraint subset tested, at every point in this session
and the previous one, either solved quickly (`OPTIMAL`) or - in the one real bug found - failed
instantly and unambiguously. Nothing has reproduced an instant-`INFEASIBLE` result on the corrected
model. What blocks task 11 now is a genuine, confirmed computational-difficulty problem with the room
assignment encoding at near-full, fully-interchangeable capacity - an engineering decision with real
tradeoffs (see the three options above), not something to resolve by continuing to guess at parameters
or budgets alone.

**Left deliberately uncommitted at this point**: `backend/tests/integration/test_h1_h12.py` (would have
made `scripts/run-checks.ps1` hang for 8+ minutes and still not pass) and this file - both committed
later, see the next log entry.

Presented the finding to the technical lead with three options (accept a larger budget, add
symmetry-breaking constraints, or reformulate room assignment for fully-interchangeable types as a
cumulative constraint). **Chose option 3** (reformulate).

---

## Session log — 2026-07-30, continued again: implementing the C-13 reformulation

Implemented the chosen option. `solver/variables.py` now computes `cumulative_room_types`: a room type
qualifies only if *every* session needing it has *every* room of that type as a candidate (computed
from the actual request, not hardcoded - a room excluded by an `exclude_slot` recommendation would
correctly disqualify its whole type, falling back to the safer per-room encoding). On the reference
instance this resolves to `{Amphi, Lab_Info, Lab_Sciences}` - `Salle` stays per-room, confirmed by a new
unit test. `assign`/`room_interval` are now only built for non-cumulative-type sessions (770 pairs,
down from thousands). `H3` (`room_assignment.py`) posts one `AddCumulative` per cumulative type instead
of a `NoOverlap` per room; `H7` posts nothing at all for those sessions - "exactly one room" becomes a
structural guarantee delivered by a new deterministic greedy labeller in `solver/engine.py`
(`_label_cumulative_rooms`), not a posted constraint. The labeller is the classical left-edge
interval-graph-colouring algorithm (sessions processed by solved start slot, ties broken by session id
for reproducibility per ADR-011; each gets the first free room of its type in canonical order) - correct
by construction, since interval graphs are perfect graphs and a colouring using exactly the peak
simultaneous-demand number of colours always exists once `AddCumulative` has bounded that peak to the
room count.

Fixed one existing unit test that assumed every session gets an `assign` entry
(`test_assign_variables_exist_only_for_candidate_pairs`) and added
`test_fully_interchangeable_room_types_are_cumulative_encoded`. All 8 tests in
`test_solver_variables.py` pass; ran the reformulated model through the same `run-checks.ps1` and it was
green apart from `pytest` picking up the (still-failing) integration test - which surfaced a real gap:
**`run-checks.ps1` ran the whole suite unfiltered**, so a slow solver-marked test would hang or fail
every future fast check. Fixed by wiring `-m "not solver"` into the `tests` step, matching what
`CLAUDE.md` already documented as the convention but nothing had actually wired in. Committed the
reformulation (`480061e`) and, separately, the integration test itself (`8f22e2b`) - it's finished,
correct work that will not silently start passing for the wrong reason once the underlying solve is
fixed, since it already independently re-verifies every rule rather than trusting CP-SAT's status.

**Measured the reformulated model against the same budgets used before, for a fair comparison** - see
the table in "Resume from here" above. **The reformulation did not resolve the difficulty.** At a
matched 480s tuned budget, conflict count went UP (405,301 vs. 29 for the old per-room encoding) while
still returning `UNKNOWN`. The reformulation cut the room-assignment variable count by roughly 90% and
is independently correct and worth keeping, but on its own it was not the fix. Two follow-on avenues are
identified and not yet tried: a constructive greedy warm-start via `model.add_hint()`, and a genuinely
larger budget (only up to 480s has been tested). Reporting back before spending more solver time on
either, since both are new decisions in their own right.

---

## Session log — 2026-07-30, continued a third time: the warm-start hint

Technical lead chose the warm-start hint. Built `solver/warm_start.py`: a most-constrained-variable
-first (MRV) greedy that reuses `variables.py`'s own domain-computation helpers (promoted from private
to public - `open_slot_map`, `day_of`, `unavailable_by_teacher`, `valid_starts`,
`candidate_rooms_for_session` - rather than recompute H4/H5/H6/H8/H9 pruning a second time), falling
back to bounded, seed-derived random restarts if the deterministic MRV order gets stuck.

**Measured the greedy's own ceiling before wiring it in, since it's cheap to test standalone (pure
Python, no CP-SAT):** MRV order alone places only 26 of 218 sessions before getting stuck. 200 random
restarts reach 188/218 best; 3,000 restarts (7 seconds of pure-Python search) reach 192/218 and plateau
there. A "least-loaded room" room-selection variant was tried too and was worse (175/218 best) - not
kept. **A complete greedy placement was never found**, on any ordering tried. This doesn't prove
infeasibility (backtrack-free greedy heuristics routinely fail on tightly-packed instances even when a
solution exists), but it is a second piece of evidence, independent of CP-SAT, that this instance sits
very close to its capacity limit.

Redesigned `WarmStart` to return the **best partial** result across all attempts rather than requiring
100% coverage (`WarmStart.covered`), so a strong-but-incomplete placement (the ~192/218 ceiling reached)
still gets used rather than discarded. Wired into `engine.py` (`_apply_warm_start`): hints `start[s]` for
every covered session, plus `assign[s,r]` for non-cumulative-type sessions (1 for the chosen room, 0 for
the rest, so the hint is a fully consistent partial assignment, not just a single free-floating value).

**Measured the hinted model against the same 480s tuned configuration used to evaluate the
reformulation.** Conflicts: 435,688 (vs. 405,301 without the hint) - essentially no change, still
`UNKNOWN`. **The warm-start hint did not help.** Three independent, legitimate techniques - the
cumulative reformulation, CP-SAT parameter tuning, and this constructive warm-start - have now been
tried, individually and combined, and none resolved the underlying search difficulty within budgets up
to 480s (8 minutes). All three are committed as real, correct improvements to the codebase regardless
(`480061e`, `c18e963`) - none of them was wasted work, but none was the fix either.

**Conclusion for this session, stated plainly per the working instructions: Phase 2 is NOT complete.**
The milestone ("a timetable without conflict on the instance") has not been reached. This is not,
however, evidence of a remaining modelling bug: nothing in this investigation - not the original H12
bug hunt, not any of today's three follow-on techniques - has ever reproduced the instant-`INFEASIBLE`
signature that would indicate one. H1-H12 are believed correct by construction, by unit test, and by
the independent re-verification built into `tests/integration/test_h1_h12.py`. What remains is a
genuine, now well-evidenced computational-difficulty problem, and the options for addressing it (a much
larger budget, a deeper model investment, or parking it) are recorded in "Resume from here" above for
whoever picks this up next.

---

## Session log — 2026-07-29

What actually happened today, so tomorrow does not re-derive it.

**Read and analysed.** All three specification documents end to end. Produced 12 findings — 11
contradictions or gaps between the documents, plus C-12 found later in the data. All in
`docs/open-questions.md` with options and owners.

**Decided four things**, each recorded as an ADR with its reasoning:
ADR-009 instance-derived normalisation bounds · ADR-010 assistant in increment 1 · ADR-011
`max_deterministic_time` instead of wall clock · C-8 roles per SRS Table 2.

**Built the repository.** 104 files. Twelve working documents, 11 ADRs, boundary types for every
module, config for both stacks. No application logic — that was deliberate.

**Placed and verified the data.** Reference archives into `data/reference/` and the generated instance
into `data/instance/`. Re-measured every figure the PDFs state as fact; all match, including the five
verifications. Wrote `data/verification/verify_instance.py` so it can be rechecked in one command.

**Ran the toolchain for the first time** after uv was installed, and it found a real bug: the layer
contracts were not loading at all (`include_external_packages` missing), so the check protecting the
central invariant of the design was silently doing nothing. Fixed, then confirmed the contract
actually fires by introducing a violation and watching the build fail on the exact line.

**Corrected two of my own mistakes.** C-11 said the instance was missing and told the next session to
write a generator — wrong, it existed. The domain enums used invented English names that could not
have parsed the real CSVs. Both corrected in place rather than quietly deleted.

**Three findings worth remembering:**

- The Kaggle archive calls itself *"Clean CSVs"*. 44% of its timeslot rows end before they start and
  83% of its room-slot pairs are double-booked. Verifying by opening files rather than reading
  documentation earned its keep.
- `.gitignore` inherited from GitHub's Python template contains `instance/` — meaning *Flask's*
  instance folder — and matches at any depth. It silently excluded `data/instance/`, the entire
  dataset. A fresh clone would have had no data and no explanation.
- OR-Tools imports and solves on Python 3.14 **and accepts `max_deterministic_time`**. ADR-011 is now
  something that has been run, not something taken from documentation.

### Done overall

- Repository structure, documentation, ADR-001 … ADR-011.
- All three specification documents read end to end; 11 contradictions and 7 architectural risks
  catalogued in `docs/open-questions.md`.
- Four decisions taken and recorded: assistant in increment 1 (ADR-010), deterministic time bound
  (ADR-011), instance-derived normalisation bounds (ADR-009), roles per SRS Table 2 (C-8).
- Layer boundaries expressed as an enforceable contract in `backend/.importlinter`.
- **Reference archives placed in `data/reference/` and re-verified** — ITC-2007 Track 3 (21
  instances), XHSTT-2014 (25 instances), Kaggle exam scheduling. Findings and measured figures in
  [`PROVENANCE.md`](../data/reference/PROVENANCE.md). ITC-2007 Track 1 remains absent; not needed
  until increment 2.
- **The reference instance is present in `data/instance/` and fully verified** — 13 CSVs, 36 KB.
  Every figure the PDFs state as fact was re-measured and matches, including all five verifications
  (Lab_Info at 95.2%, heaviest load 12 periods, smallest margin 11 free slots, 425 students matching
  declared group sizes). Checker: `scripts/verify-instance.ps1`. **C-11 is resolved** — the scaffold
  originally recorded the instance as missing, which was wrong.
- Domain enums corrected to the instance's actual vocabulary (`PROMO`/`TD`/`TP`, `Amphi`/`Salle`/
  `Lab_Info`/`Lab_Sciences`, French teacher ranks) and `occurrences_per_week` added to `Session`.
- **C-12 recorded** — S5 carries weight 0.20 and has no input data in the schema.

---


---

## C-13 as originally recorded — the superseded analysis

Moved here from `docs/open-questions.md` on 2026-07-30. The conclusion below is **wrong** — kept
because the measurements are real, and because how a well-evidenced conclusion came to be wrong is
the most useful thing in this archive. The correction is C-13 in `docs/open-questions.md`.


H1, H3, H7 and H12 were built, reviewed, and — after finding and fixing a real bug in H12's original
grouping (see `docs/status.md`, 2026-07-30) — are believed correct: no test at any point has reproduced
an instant, sub-second `INFEASIBLE`, which is the signature the project's own docs (R-2) associate with
a modelling bug at this instance's occupancy. Instead, solving the combined model returns `UNKNOWN`
after minutes of search — CP-SAT neither finds a feasible timetable nor proves there isn't one.

Root cause, confirmed by inspecting the instance directly (no solver call needed): `Lab_Info` (6 rooms,
95.2% occupancy) and `Lab_Sciences` (2 rooms, 85.7%) are **fully interchangeable room types** — every
session needing that type gets *every* room of that type as a candidate (min candidate count equals max
candidate count equals room count, for both). Full interchangeability at near-full capacity is the
textbook hard case for generic CP/MIP search, because the solver has to distinguish between assignments
that are actually equivalent. `Amphi` is also fully interchangeable (2/2) but only 57% occupied, so it
isn't believed to be part of the difficulty. `Salle` is partially interchangeable (5–10 of 10 rooms,
depending on group size) at 29% occupancy — plenty of slack, also not implicated.

Three ways were identified to proceed:

- **(a)** Accept a much larger deterministic budget (many minutes) as the current reality for a first
  timetable, and revisit performance later. Lowest engineering risk; leaves the "<60s, an estimate"
  target unmet for now and Phase 2's milestone unconfirmed for a long time.
- **(b)** Add explicit symmetry-breaking constraints among interchangeable rooms of the same type (a
  canonical ordering that prunes equivalent assignments). Keeps the current `assign[s,r]` +
  optional-interval encoding; moderate risk of a new subtle bug written under time pressure.
- **(c)** Reformulate room assignment for the fully-interchangeable types (`Amphi`, `Lab_Info`,
  `Lab_Sciences`) as a `cumulative` constraint (simultaneous demand ≤ room count) instead of per-room
  `NoOverlap` + `assign` booleans, and label the actual room afterward with a simple greedy sweep —
  correct by construction (an interval-graph-colouring argument: if cumulative demand never exceeds
  capacity, a per-room labelling always exists). Keep the existing encoding for `Salle`.

**(c) was chosen and implemented 2026-07-30** (`solver/variables.py`'s `cumulative_room_types`,
`solver/constraints/room_assignment.py`, `solver/engine.py`'s `_label_cumulative_rooms` - commit
`480061e`). It is correct, unit-tested, and cut the room-assignment boolean count from thousands to 770
(only `Salle` still uses `assign[s,r]`). **It did not resolve C-13 on its own**: at a matched 480s tuned
budget, the reformulated model still returned `UNKNOWN`, with conflict count *higher* than the old
encoding's at the same budget (405,301 vs. 29). The reformulation remains worth keeping - it is a real,
verified improvement to the encoding - but the underlying search difficulty needs a different or
additional lever.

**A constructive greedy warm-start was also tried, 2026-07-30, and also did not resolve C-13**
(`solver/warm_start.py`, commit `c18e963`). A most-constrained-variable-first (MRV) greedy, with bounded
random restarts on failure, was measured standalone before wiring it in: MRV alone places only 26 of
218 sessions before getting stuck; 3,000 random restarts plateau around 192/218 - a complete greedy
placement was never found on any ordering tried. The best partial result (`WarmStart.covered`) was hinted
to CP-SAT via `model.add_hint()` regardless, on the reasoning that CP-SAT is typically much faster at
*verifying* a supplied candidate than at *finding* one from scratch. Measured against the same 480s
tuned configuration used for the reformulation: conflicts=435,688 (vs. 405,301 without the hint) -
essentially unchanged, still `UNKNOWN`. **The hint made no meaningful difference.**

**Three independent, legitimate techniques - the cumulative reformulation, CP-SAT parameter tuning, and
the constructive warm-start - have now been tried, individually and combined, and none resolved the
underlying search difficulty within budgets up to 480s (8 minutes).** All three remain committed as
real, correct improvements (the reformulation and the warm-start module are both independently useful
and unit-tested), but none was the fix. This is no longer a "try the next idea" situation.

**What's left, genuinely untested**, in rough order of promise:

- A much larger budget (tens of minutes to hours) - only up to 480s has actually been tried.
- Symmetry-breaking specifically on `Salle` (option (b), narrowed to the one remaining per-room type) -
  considered unlikely to matter given its 29% occupancy, but not directly tested.
- A more sophisticated warm-start construction (real backtracking, or a matching-based room assignment
  rather than greedy first-fit) that might close more of the ~87% coverage ceiling reached so far -
  though the fact the ~87%-covering hint barely helped is a discouraging sign for this direction.
- Reconsidering the model more radically (additional redundant/implied constraints to aid propagation,
  or a different global-constraint structure) - the largest investment of anything considered so far.

A second, smaller finding from the same investigation: under `num_workers=0` (parallel search),
`max_deterministic_time` did not tightly bound the search the way ADR-011 assumes for a single-worker
budget — a run configured for 60s deterministic time consumed 247.98 deterministic-time units before
the wall-clock ceiling actually stopped it. Doesn't undermine ADR-011's reproducibility argument, but
the deterministic-time parameter cannot yet be trusted as the primary stopping mechanism in parallel
mode without further calibration.

**Blocks:** Task 11 (integration test) and therefore Phase 2's stated milestone ("a timetable without
conflict on the instance"). **Owner:** technical lead.


---

# Archive — the completed-phase record, moved from `docs/dashboard.md` on 2026-08-06

**Why this is here.** `docs/dashboard.md` is the handoff page and `CLAUDE.md` says it is *"usually
the only file you need before starting work"*. It had grown to 668 lines by carrying the full
milestone-by-milestone account of four completed phases, which a cold session pays for in context and
never needs. That material is **moved, not deleted** — every closing audit, every measurement and
every recorded limitation is below, unedited.

⚠️ **Read this only for forensics**, as `CLAUDE.md` says of this whole file: to check what was
already tried before repeating an experiment, or to understand why a past decision was taken. The
dashboard keeps a summary of each phase and points here.

## Phase 3 — complete 2026-07-31. What was built, and what Phase 4 inherits

**Completed 2026-07-31.** All four completion criteria met, the milestone met, six closure items done,
and the audit that closed the phase left no known contradiction between documents. Two acceptance
criteria moved from unmet to met (three candidates; reproducibility), taking the total to **3 of 9**.

**What it set out to achieve.** A *portfolio*, not a timetable. Several valid timetables produced under
different weight profiles, ranked by an exact weighted sum, with the difference between any two
decomposed criterion by criterion.

**Why it exists.** The department will not adopt a timetable it cannot argue with. The score is linear
precisely so the explanation *is* the calculation read term by term, recomputable by hand from the
sub-scores and weights recorded with the run. That is the whole reason a weighted sum was chosen over
lexicographic ordering or a learned ranker (ADR-002).

**C-4 and C-12, resolved.** `docs/open-questions.md` carries the formulas for all seven criteria and the
reasoning for each choice (including the ones that were judgment calls, not derivations — S4's resource
and S6's target). S5 uses a labeled proxy (edge-of-day placement), not real preference data — recorded
as a deliberate, scope-driven stand-in for the real fix (a genuine preferred-window column), not a
definition of teacher preference.

**Built.**

| Module | What it does |
|---|---|
| `analysis/instance_view.py` | Shared hierarchy and day/period lookups, built once |
| `analysis/criteria.py` | The seven `Criterion` implementations over realised placements |
| `analysis/scoring.py` | `DefaultScorer`, `evaluate_candidate`, weight renormalisation |
| `analysis/ranking.py` | `DefaultRanker` — rank, decompose, dominance, **recommend** (FR-16) |
| `solver/objective.py` | The same seven formulas as CP-SAT expressions |
| `solver/engine.py` | Posts the objective, and builds occupancy at all, only when a criterion carries weight; sets `interleave_search`; withholds the warm start under an objective |
| `recommendations/translator.py` | The closed 3-action catalogue translated to a `RunOverride` |
| `services/portfolio.py` | The three profiles, one seed, sequential solves, duplicates removed, survivors ranked under one weight vector |
| `validation/itc2007/` | The benchmark harness — **not product code**, and nothing shipped may import it |

**Tests went from 27 to 125** (103 fast + 22 solver-marked). The two that carry the most weight are
`tests/integration/test_objective_matches_analysis.py`, which requires the solver's objective and the
analysis layer's recomputation to agree *numerically* on the same placements — it is what caught S6's
28× scale error, which reading the two implementations side by side did not — and
`tests/integration/test_reproducibility.py`, which pins reproducibility at the **production** worker
count rather than at a safe proxy.

**Validated on published instances (`docs/testing-strategy.md` §1).** `optiedt/validation/itc2007/`
models ITC-2007 Track 3 separately — a different problem, so no code is shared with `solver/` and the
eighth import contract keeps the dependency one-way. Its cost function reproduces the published cost of
seven solutions the archive ships, exactly, component by component; that agreement is what makes the
rest of its output checkable rather than merely self-consistent.

**Result: 21 of 21 timetables violate no hard constraint**, judged by re-deriving all four ITC-2007
constraints rather than trusting CP-SAT's status. **The cost gap is large — median 1269 % against the
seven instances the archive gives figures for — and that is expected**: the references are
metaheuristics tuned for this problem, several with no time limit, against ~50 s of exact search, and
the strategy document states plainly that beating them was never the objective. What makes the gap
interpretable is that **the model is demonstrably correct**: `comp11` solved to **cost 0, proven
optimal**, and `comp01` reaches the published optimum of **5** given more search. Both sweeps returned
**identical costs on all 21 instances** despite per-instance wall clock differing by up to 2× — ADR-011's
deterministic budget doing its job on instances the project did not design. Figures in `docs/status.md`.

**Not built, and why.** H10's target-slot/room gap in `solver/variables.py` is **not** closed — it needs
`solver/variables.py` and `solver/interfaces.py` changes, and nothing before Phase 5's run record can
exercise it. `recommendations/translator.py` therefore returns a `RunOverride` (plain domain data), not
a `SolverInput` — see "Known risks" above for why the existing `Run`/`Candidate` schema cannot support
building one directly. **Regeneration is consequently half-built**: the catalogue and the translation
of all three actions exist; turning an accepted recommendation into an actual new run
needs run/instance context that arrives with Phase 5's run record.
⚠️ **Corrected 2026-08-06: this said the translation `is tested`. It is not.** No test in the
repository imports `optiedt.recommendations` - verified by grep across `backend/tests/`. The
catalogue and `translator.py` have **zero coverage**, and the claim survived because `recommend()`
in `analysis/ranking.py` IS tested and carries a similar name. Two different things, one word. That split is deliberate and
recorded, not an omission — but do not read the phase's work row as claiming end-to-end regeneration.

**S6 (room efficiency) is scored fully but optimised only partially.** `analysis/criteria.py` scores
every room correctly after the fact. `solver/objective.py` can only post a CP-SAT term for
non-cumulative room types (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences, C-13) have no
per-room decision variable at all; a specific room is chosen by a deterministic post-solve labeller the
objective cannot see or influence. Closing this would mean changing `solver/variables.py`.

**Which documents are authoritative, still.**

| Question | Authority |
|---|---|
| The three formulas, bounds policy, the four required properties | [`docs/scoring-and-explanation.md`](scoring-and-explanation.md) |
| The seven `v_i`/bounds formulas actually chosen, and why | [`docs/open-questions.md`](open-questions.md), C-4 and C-12 |
| Criterion codes, names, default weights | `data/instance/constraint_catalogue.csv` — **not** the PDFs |
| Which variables the objective may read | [`docs/constraint-model.md`](constraint-model.md), C-7 section |
| Layer permissions | [`docs/architecture.md`](architecture.md) + `backend/.importlinter` |
| Recommendations and regeneration | [`docs/ai-integration.md`](ai-integration.md) |
| What the ITC-2007 figures do and do not prove | [`docs/testing-strategy.md`](testing-strategy.md) §1 |
| ITC-2007 reference costs | The archive's own bundled report — transcribed in `validation/itc2007/published.py`, **never from an outside lookup** |

**Constraints already implemented.** All twelve hard constraints. H1, H3, H7, H12 are real CP-SAT
postings and carry assumption literals; H4, H5, H6, H8, H9, H10 are domain restrictions applied at
variable construction; H2 is subsumed by H12 and H11 by H3, both registered as documented no-ops.
**H10 is registered but dormant, still** — `build_variables` refuses to run if any session is locked,
because there is no way yet to supply the target slot/room. The reference instance has no locked
sessions. This did **not** get filled this session (out of scope, see above); recommendation-driven
regeneration is what will first need it.

**Constraints remaining.** None for the weekly model. X1–X4 and SX1 are the examination model —
increment 2.

---


---

### Phase 4 — Web interface · ✅ **complete 2026-08-01**

**Purpose.** The complete path from a teacher declaring availability to a published timetable.

**Completion criteria — three of four met, and the fourth is not automatable.**
- Generation screen. ✅ **Met** (M3), verified against the real solver.
- Side-by-side comparison with contributions. ✅ **Met** (M5) — and it ticked the acceptance criterion,
  which needed *displayed* figures rather than computed ones.
- Timetable views by teacher, group, room, lab. ✅ **Met** (M4); the "lab" view is FR-18's occupancy
  report, whose totals match `verify-instance` exactly.
- Availability grid filled in **under 5 minutes without training**. ⚠️ **Built (M6), not verified.**
  The criterion is about a person and needs a timed walkthrough with a teacher who has not seen the
  screen. **This is the one thing Phase 4 owes**, and it is carried to Phase 6 with the other
  acceptance work.

**Dependencies.** Phase 3's algorithms — score, ranking, decomposition, dominance, the recommendation
rule and the portfolio — existed to build the screens on. Both open questions that landed here were
decided: **C-12(a)** resolved (two states, because the schema has no third to record) and **C-14**
deferred (no dominance signal shipped, rather than one that can never fire). Both were recorded in
`docs/open-questions.md` with their reasons **before** the code was written.

**Status. COMPLETE — 6 of 6 milestones, closing audit passed 2026-08-01.**

| # | Milestone | State |
|---|---|---|
| **M1** | API foundation — `GET /api/instance`, FR-2 availability read/write, wire format pinned | ✅ **done** |
| **M2** | Run lifecycle — `services/runs.py`, `tasks/executor.py`, `POST /runs` → 202, polling, candidate/comparison/dominance/recommendation endpoints | ✅ **done** |
| **M3** | Frontend shell + generation screen (FR-13, FR-5, FR-6) — **verified end to end against the real solver** | ✅ **done** |
| **M4** | Timetable views (FR-7, FR-18) — by teacher, group, room, plus room occupancy | ✅ **done** |
| **M5** | Comparison screen (FR-14, FR-15) — **ticks acceptance criterion 3**. ⚠️ Dominance signal deliberately NOT built, held for **C-14** | ✅ **done, minus the blocked part** |
| **M6** | Availability grid (FR-2) — **two-state**, C-12(a) resolved 2026-08-01 | ✅ **done** |

⚠️ **Scope note, stated rather than assumed.** Phase 4 is written as "the web interface", but no screen
can exist without an API, and this block already anticipated it ("built alongside this phase's
`services`/`db` work"). Phase 4 therefore delivers **the screens plus the minimum API to reach them,
with the run store in memory**. Authentication and RBAC (FR-11), PostgreSQL and the diagnosis run stay
in Phase 5. **The API has no authentication yet and must not be exposed beyond a development machine.**

#### The closing audit, 2026-08-01

**Six passes; the sixth found nothing.** It found **17 defects**, plus one the audit introduced and
caught on the next pass (a fix that duplicated a paragraph) — worth recording, because it is why a
clean pass has to be a *whole* pass and not a spot check of what you just edited.

The useful part is the shape of them: **not one was caught by `run-checks.ps1`**, which was green
before the audit started, green after every fix, and green throughout. A validation suite proves the
code does what its tests say; it cannot notice that a document describes a different system.

The Phase 3 close taught the method and this audit confirmed it: **compare documents against the
repository, never against other documents.** Every defect below was found by checking a claim against
`git`, a file count, a `grep`, or the running application — not by reading two documents side by side.

| Kind | Found |
|---|---|
| **Stale status** | Both `dashboard.md` and `status.md` still opened with "Phase 4 has not started", the phase block still read "IN PROGRESS — M1 of 6", and the health row still said 125 tests and 8/8 contracts. **The header of the handoff file is what a cold session reads first** — the same defect the Phase 3 close found, recurring |
| **Wrong counts** | "ten steps" in `run-checks.ps1` (there are 8) · "11 of 25 requirements" (12) · "3 of 9 acceptance criteria" (4) · a 55 % progress bar (75 %) · a duplicated caption my own fix introduced |
| **Claims contradicted by the code** | ADR-005 and `architecture.md` both list *"candidates visible as they are produced"* as a delivered benefit; `portfolio.py` returns the whole portfolio at the end, so the screen shows `SOLVING` for 105–150 s and everything arrives at once. ADR-005 also says run state "lives in the database" — it is in memory. `frontend/README.md` repeated the incremental claim and described four screens that do not exist |
| **Comments contradicting each other** | `schemas.py` said `domain.ts` declares `preAnalysis`/`diagnosis` on its `Run`; `domain.ts` says it deliberately does not. Two files describing each other, both wrong |
| **Over-claims** | "The frontend computes nothing" — falsifiable by one grep, and an over-claim invites the reader to conclude the rule is not meant seriously. It computes no *score* and decides no *ranking*; it does sort grid axes and round for display |
| **Dead code** | `useCandidates` and `useDominance` (frontend hooks nothing called — the second because C-14 deferred the display) and `RunSummary` in `services/runs.py`. Removed; the *endpoints* stay, tested and deliberate |

**What the audit did not find:** any architecture violation (9/9 contracts kept throughout), any broken
link, any unresolved TODO, and no defect in what the screens actually compute — the occupancy view still
reconciles with `verify-instance` to the period.


---

### Phase 5 — Pre-analysis in-app, diagnosis, auth, run record · ✅ **complete 2026-08-04**

**Purpose.** An infeasible instance must produce a report naming the rules in conflict, not a
timeout; every published timetable must trace back to its run, seed and weights.
**Completion criteria.** FR-12 reports structural risks through the API; the diagnosis run returns a
sufficient conflict set; a teacher account sees only its own data; runs are recorded.
**Dependencies.** C-6 is already resolved (only H1, H3, H7, H12 carry an assumption literal, so the
conflict report can name an actionable rule). **Phase 4 left the seams in place**: `RunStore` and
`AvailabilityStore` are Protocols with in-memory implementations, so FR-19 substitutes database-backed
ones without touching a router; `RunState` already carries `PREANALYSIS`, `DIAGNOSING` and `DIAGNOSED`.

| # | Milestone | State |
|---|---|---|
| **M1** | **Pre-analysis in the application (FR-12)** — the five checks with both bounds, run in `PREANALYSIS`, recorded, displayed | ✅ **done 2026-08-03** |
| **M2** | **Diagnosis run (FR-8)** — rule withdrawal over plain subset solves, `INFEASIBLE → DIAGNOSING → DIAGNOSED`, conflict report screen | ✅ **done 2026-08-04**, including **C-17 resolved** |
| **M3** | **Run record (FR-19)** — `db/` models, `migrations/env.py`, first migration, SQL-backed stores behind the existing Protocols, against **real PostgreSQL** | ✅ **done 2026-08-04** |
| **M4** | **Authentication and rights (FR-11)** — users, JWT, RBAC, teacher scoping, login screen, seed command | ✅ **done 2026-08-04** |
| **M5** | **Publication + traceability** — closes *"every published timetable traces back to its run, seed and weights"* | ✅ **done 2026-08-04** |
| **M6** | **Closing audit + documentation** | ✅ **done 2026-08-04**, eight defects found |

**Three scope decisions taken before any code, on 2026-08-03.** All three were flagged rather than
assumed, because none is settled by the specification:

1. **Publication is IN Phase 5, as M5.** It appears in the phase's *purpose* sentence and in a written
   acceptance criterion, but in none of the four completion criteria — and Phase 4's milestone wording
   ("the complete path … to publication") already left it owed. Building it is the only way to tick
   that criterion.
2. ~~**Persistence tests run on SQLite.**~~ **REVERSED 2026-08-04 after re-verifying the environment.**
   Docker is running and PostgreSQL 17 is reachable through `Settings.database_url`, so the store
   tests run against the engine the project actually ships. `run-checks.ps1` **fails** when Docker is
   up but the container is not — that is a forgotten `docker compose up -d`, and it is actionable —
   and **skips** when Docker itself is absent, matching the existing `node_modules` precedent.
3. **Accounts come from a seed command**, `python -m optiedt.db.seed`: one person in charge, one
   administrator, one student and one account per instance teacher. No requirement describes
   registration, and SRS Table 2 (authoritative per C-8) gives the administrator account management
   without saying where the first administrator comes from. **To be recorded in
   `docs/open-questions.md` with its reason before M4's code**, per this project's own rule.

**FR-23 regeneration is explicitly out of scope.** M3's run record unblocks it, and H10's dormant gap
with it (item 8 of `docs/status.md`'s "Next, in order"), but it is in no Phase 5 completion criterion.

#### M1 — what landed, 2026-08-03

`optiedt/preanalysis/verifications.py` implements the five checks; `tasks/executor.py` runs them
against **the instance the run is about to solve** (declarations included, resolved once and handed to
both stages); `RunOut.preAnalysis` returns them; `features/generation/PreAnalysisReport.tsx` displays
them.

Four things are worth carrying forward:

- **Both bounds are ported**, and `tests/unit/test_preanalysis.py::test_the_original_room_mix_is_caught`
  is the guard: it reconstructs the pre-C-13 room mix and requires the contiguity bound to name
  computer laboratories short by **14** windows and science laboratories by **2** — on an instance the
  period bound passes at a comfortable 95.2 %. **If that test ever passes trivially, the blind spot is
  back inside the product.**
- **The report shows figures, not five green ticks.** SLOT_COVERAGE passes on the reference instance
  *and* says Lab_Info is the binding resource at 90.9 % of two-period windows against 71.4 % of
  periods. A verdict-only report would reproduce exactly the reading error C-13 cost three sessions.
  `PreAnalysisReport.test.tsx` asserts the figures are in the DOM, because no backend test can.
- **The two implementations are compared numerically**, not trusted to agree:
  `tests/integration/test_preanalysis_matches_verifier.py` re-derives every figure from the raw CSVs.
  Same guard, same reasoning as `test_objective_matches_analysis.py`.
- **An empty check list means the stage did not run**, never "verified, nothing wrong" — asserted on
  both sides.

⚠️ **One half of verification 5 is deliberately not ported.** `Instance` excludes `Student`
(increment 2), so "425 students match the declared subgroup sizes" stays with `verify-instance.ps1`,
and the in-application check says so in its own report rather than passing for the documented one.

⚠️ **Verified rather than asserted, on a real run:** the report renders live during `SOLVING`, every
figure matching `verify-instance` exactly, and **it is still displayed when the run lands in `FAILED`**
(budget 3 → `UNKNOWN`). That is the C-13 case: when CP-SAT cannot prove an infeasibility, the
pre-analysis report is the only thing that says whether the instance is structurally sound.

⚠️ **Raised, not decided: the report's `detail` text is English inside a French interface.** This
follows existing precedent — `RECOMMENDATION_RULE` ("highest score under the weights in force") has
been displayed verbatim inside a French sentence on the comparison screen since Phase 3 — so M1
matched the convention rather than inventing a localisation layer for one component. **The convention
itself is worth a decision** before the report goes in front of the supervisor.

#### The closing audit, 2026-08-04

**Eight defects, and not one was caught by `run-checks.ps1`** — green before the audit, green after
every fix, green throughout. A validation suite proves the code does what its tests say; it cannot
notice that a document describes a different system. Same method as Phase 4: **compare documents
against the repository, never against other documents.** Every defect below was found by checking a
claim against a file count, a `grep`, `.importlinter`, or the running application.

| Kind | Found |
|---|---|
| **Wrong counts** | The Validation row still said "eight steps", "9/9 contracts", "60 files", "194 fast tests" (nine, 10/10, 71, 227). The Tests row said "246 backend + 19 frontend" (287 + 24). The Phase 6 block said "four of nine acceptance criteria" (six) |
| **Claims contradicted by the code** | The API row still said "Both stores are **in memory** … PostgreSQL is not needed until runs must survive a restart" — false since M3. `frontend/README.md` marked `features/conflicts/` as unbuilt when M2 built it, said "four directories carry a screen" when six do, and listed neither `auth/` nor `publication/` |
| ⚠️ **A correction that itself went stale** | ADR-005 carries a correction dated 2026-08-01 saying run state "does not live in the database. It is in memory". M3 made that false four days later. **A note saying "this is not built yet" acquires an expiry date the moment someone builds it, and nothing fails when it passes.** ADR-005 now carries a second correction saying so |
| **A milestone claim frozen in the past** | "Milestone reached" still described Phase 4's. Phase 5's own milestone was reached in M2, and M5 completed Phase 4's — publication was the part it could not build |
| **Documentation that never learned about new work** | `docs/testing-strategy.md` described neither the `database` marker (declared in `pyproject.toml`) nor any of the seven test files M1–M5 added |

**What the audit did not find:** any architecture violation (10/10 contracts kept throughout, and both
new contracts were verified to fire before being relied on), any broken link, any `TODO` in source, any
module path quoted in a document that does not exist, and no error in `open-questions.md`'s own
bookkeeping — seventeen codes, C-1 to C-18 with no C-10, four open and thirteen resolved, all
consistent.

#### M5 — what landed, 2026-08-04

`services/publications.py`, `api/routers/publications.py`, a `publications` table with migration
`04462f0db630`, and a publications screen with the trace displayed in full. **The acceptance
criterion is met.**

- **The trace is ASSEMBLED, never stored beside the publication.** A publication names its candidate
  and its run; the seed, the weight vector, the model version and the budget are read from the run
  record on every request. Copying them would create a second answer to *"what produced this?"*, free
  to drift from the first — and the criterion exists precisely so that question has one answer.
- **The publication points at the candidate rather than copying the placements.** A candidate is
  immutable (invariant 6), so pointing is both sufficient and safer: two records of one timetable can
  disagree, and then nothing says which was published. The foreign key has **no cascade** — a
  published timetable is a record of something the department did, and deleting a run that has one
  now fails rather than erasing it.
- **The trace is returned by LISTING, not only by publishing.** A criterion satisfied only in the
  response to the act that created the record is not satisfied at all; nobody re-publishes a
  timetable in order to read it.
- ⚠️ **The whole weight vector is displayed, including the zero-weight S10.** A score is only
  recomputable by hand from every weight, and `TraceTable.test.tsx` pins that a summary cannot creep
  in.

⚠️ **Verified on a real solve, not a fake**: seed 7, budget 90, 3 distinct candidates in 206.9 s.
The top candidate was published, **the API process killed**, and a fresh process returned the
complete trace — run, seed, all seven weights, model version, budget, author, and all 218
placements. A teacher asking for `/publications` got **403**.

#### M4 — what landed, 2026-08-04

`core/security.py`, `services/users.py`, `api/routers/auth.py`, the RBAC dependencies in
`api/deps.py`, a `users` table with migration `4553e7a29780`, the seed command, and a login screen.
**The acceptance criterion is met**: a teacher account obtains only its own availability.

- ⚠️ **`passlib` was a declared dependency and did not work.** passlib 1.7.4 (2020, unmaintained)
  reads `bcrypt.__about__`, removed in bcrypt 5, and its `hash()` raised *"password cannot be longer
  than 72 bytes"* on ANY input. Replaced with `bcrypt` directly — four lines — rather than pinning
  bcrypt backwards to keep an unmaintained wrapper alive. The 72-byte limit is now **refused**, not
  truncated: bcrypt ignores the tail silently, so a long password would be far weaker than its owner
  believes.
- **Which teacher a caller is comes from the TOKEN.** Phase 4 took it from the path and said so; this
  is the line it left. An account with no `teacher` link is refused every grid rather than defaulted
  to one.
- **The hash never leaves the store.** `domain.User` has no password field, so no router, schema or
  log line can serialise one. `authenticate()` takes a password and returns a credential-free `User`.
- ⚠️ **`TokenOut` disables the camelCase alias generator, and must.** Pydantic MERGES `model_config`
  with the base class's, so declaring only `frozen=True` left `ApiModel`'s generator in force and the
  endpoint answered `accessToken`/`tokenType` — a 200 no OAuth2 client can read. Caught by
  `test_rbac.py` on its first run.
- **`test_rbac.py` uses real tokens.** Every other API test overrides `current_user` so that a test
  about the wire format is not also a test about signing in; this one must not, because overriding
  the dependency would test the override.

⚠️ **Account management through the interface is NOT delivered.** SRS Table 2 gives the
administrator that right; accounts come from `python -m optiedt.services.seed` instead, which
**refuses to run against an installation that already has accounts**. C-18 records the decision and
what it leaves owed.

⚠️ **Verified end to end, not asserted**: signed in as `t001` — the interface offered no
Génération link, the teacher field was read-only at `T001`, and the API answered **403** for
`T002`'s grid and for `POST /runs`. As `responsable`, the same screens offered the 44-teacher
dropdown and the full navigation. A wrong password and an unknown username returned identical 401s.

#### M3 — what landed, 2026-08-04

`db/models.py`, `db/repositories.py`, `db/session.py`, the first alembic migration, and
`services/stores.py` — the factory that decides which store a process uses. **No router changed**,
which is exactly what Phase 4's Protocols were for.

- **A tenth import contract, `api ⇸ db`**, verified to fire before being relied on (a deliberate
  violation was injected and the build broke on it). The natural wiring — `api/deps.py` importing
  `SqlRunStore` — would have put the ORM in the router layer; the factory keeps the API asking for a
  store and never learning what it is.
- **The store-contract suite found a real divergence on its first run.** One suite runs over both
  implementations, and the *in-memory* store failed the invariant-6 test: it replaced the whole record
  on `save`, so a later revision could overwrite a recorded candidate, while the SQL store refused.
  Fixed in `services/runs.py`. That divergence would otherwise have surfaced only in production, after
  a restart, as a run that came back different from the one written.
- ⚠️ **A passing test was hiding a dependency.** When `persistence` began defaulting to `database`,
  `test_availability_api.py` kept passing *and quietly wrote two rows into the developer's own
  database* — it clears the dependency cache but never overrides the store. `tests/conftest.py` now
  forces `OPTIEDT_PERSISTENCE=memory`, and the database tests take an explicit session factory against
  a database of their own (`optiedt_test`). A green suite that silently depends on PostgreSQL and
  mutates it is worse than a failing one.
- **Verified rather than asserted:** a run was launched through the API, the process killed, and a
  **fresh process** read it back complete — seed, budget, model version, all seven weights, a
  timezone-aware timestamp, the recorded error and all five pre-analysis checks.

⚠️ **`alembic current` failed before this milestone** — `alembic.ini` was configured, `migrations/`
held only a `.gitkeep`, and `env.py` did not exist. Two traps came with initialising it, both now
guarded in comments: `Base.metadata` is empty until the model module is imported (an autogenerate
against partial metadata emits DROPs, and the test fixture hit exactly this and created no tables),
and the URL must come from `Settings` rather than `alembic.ini` so that migrations and the API cannot
target different databases.

#### M2 — what landed, 2026-08-04, and the question it raised

`CpSatSolver.diagnose` posts the four assumable rules under enforcement literals and reads the unsat
core back; `tasks/executor.py` walks `INFEASIBLE → DIAGNOSING → DIAGNOSED`; `RunOut.diagnosis` carries
it; `features/conflicts/ConflictReport.tsx` displays it. `ConstraintBuilder.apply` gained an optional
literal so **stage 2 and stage 3 post through the same builders** — a separate diagnosis model could
name a conflict that does not exist in the model actually solved, and nothing would catch it. The 22
solver-marked tests re-derive H1–H12 from the raw CSVs and still pass, so nothing was dropped.

`DiagnosisResult` **moved from `solver/interfaces.py` to `domain/entities.py`.** Leaving it in the
solver would have forced `api/schemas.py` to reach it through a re-export in `services` — legal, since
`api ⇸ solver` forbids direct imports only, and evasion rather than compliance. A shape three layers
must name belongs to the layer all three may import.

Three findings worth carrying:

- ⚠️ **C-17, and it is the important one.** The mechanism the documentation specified — enforcement
  literals passed as assumptions — was built, tested and then **measured unusable at reference scale**.
  A literal takes its constraint out of presolve: an area contradiction a plain solve proves in
  **0.0 s** returned **`UNKNOWN` after 240 s**, and four times the budget changed nothing. Stage 3 now
  **withdraws one rule at a time and solves plainly**, which answers **`('H3',)`, minimal, in 1.9 s**
  on that same instance. Two of the three properties `architecture.md` called "imposed by CP-SAT" were
  imposed by the assumption mechanism and changed with it; only "no objective" survives as imposed.
- **Several minimal explanations can exist and one is reported.** When two rules both forbid the same
  placement, either alone explains the conflict. Rules are withdrawn in catalogue order, so the answer
  is arbitrary between them but **reproducible** — which is what matters when the report tells a user
  which rule to change. Measured: one teacher, one room, one slot, two sessions → `('H3',)`, every time.
- **`is_minimal` is evidence, not a label.** Each removal is tested, so a set is normally irreducible
  — but a removal the solver cannot decide keeps its rule *for want of evidence*, and the flag goes
  false. The screen has two different paragraphs for the two cases.
- **`DIAGNOSED` does not mean a conflict was named.** It can be conclusive-and-empty (no *withdrawable*
  rule explains it — the conflict is in the data) or inconclusive (no proof was found). Measured on
  the pre-C-13 room mix: **empty and not conclusive**, because CP-SAT cannot prove that infeasibility
  at all — the pre-analysis catches it in milliseconds instead. Neither may read as "no problem found".

