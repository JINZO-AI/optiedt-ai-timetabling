# Status

**Increment 1 of 2 · Phase 2 milestone REACHED — a conflict-free timetable is produced on the
reference instance in ~3 s. Last updated 2026-07-30.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

---

## ▶ Resume from here — copy this to continue

> Resume OptiEDT. Read `CLAUDE.md`, then this file's "Session log — 2026-07-30, fourth continuation",
> then C-13 in `docs/open-questions.md` (now **RESOLVED**). Do not open the PDFs.
>
> **Phase 2's milestone is met.** H1–H12 are built, correct, and demonstrated: the reference instance
> solves in **2.8–3.3 s** (deterministic time 0.13–0.21, measured across seven seeds on the production
> default configuration) and all 27 tests pass, including
> `tests/integration/test_h1_h12.py`, which re-derives every hard constraint from the raw CSVs rather
> than trusting CP-SAT's status. **Do not redo any of this work, and do not go looking for a
> solver-performance problem — there isn't one.**
>
> **The C-13 "room-assignment symmetry" investigation reached the wrong conclusion and is now
> resolved.** The model was always correct; the *instance* had no solution. Every laboratory session
> spans two periods, a two-period session must fit inside one day, and a 5-period day offers a room
> only two such windows — so a room offered 11 two-period windows a week against demand that needed
> more. `Lab_Info` needed 80 windows and had 66; `Lab_Sciences` needed 24 and had 22. The three
> techniques tried before (cumulative reformulation, parameter tuning, greedy warm-start) all
> "failed" because they were searching for a solution that did not exist. **Fixed by re-typing three
> classrooms as laboratories** — `Salle` 10 → 7, `Lab_Info` 6 → 8, `Lab_Sciences` 2 → 3, total room
> count still 20, calendar and session mix untouched.
>
> **The lesson worth keeping.** Pre-analysis verification 2 compared *period totals*
> (`rooms × open_slots`) and reported a comfortable 95.2 %. That bound is necessary but not
> sufficient: it cannot see that a 5-period day wastes one period per room whenever the sessions are
> 2-period. The instance was really **121 % subscribed**. The check whose stated job is to separate
> "this instance has no solution" from "the model has a bug" gave the wrong answer, and three sessions
> went hunting a bug that did not exist. `data/verification/verify_instance.py` now applies both
> bounds; **the FR-12 in-application port must carry the contiguity bound too.**
>
> **C-7 is also resolved and implemented** (`solver/occupancy.py`, 2026-07-30): `y[s,t]` means
> *occupies* `t`, channelled from start indicators `x[s,t₀]`, built **on demand** because it costs the
> feasibility solve 2.5×. **Phase 2's modelling is therefore complete** — H1–H12, a conflict-free
> timetable, and the accounting variables the objective will read.
>
> **Next: C-4, and it is not a keyboard decision.** Seven soft criteria each need a `v_i` and a
> `min_i`/`max_i`, and **none has one**. The objective cannot be encoded until they exist, and
> inventing them in code is precisely what `CLAUDE.md` forbids. **C-12 must be settled in the same
> pass** — S5 carries weight 0.20 with no input data, and if it measures identically zero the
> teacher-favouring profile collapses onto another one and the three-candidate acceptance test fails
> for an invisible reason (C-5). Both are the technical lead's, before Phase 3.
>
> Also still owed, and blocked on the same decision: the objective's **auxiliary variable count**
> (first/last occupied period per group-day, gap indicators). It follows from the criterion formulas,
> so it is recorded as unknown rather than guessed.

---

## ▶ Superseded resume block — kept only so the correction is legible

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

## Where the project is

| | |
|---|---|
| **Current phase** | **Phase 2 complete.** H1–H12 built and demonstrated correct (conflict-free timetable in ~3 s, every hard constraint re-verified from raw CSVs); C-13 resolved — the model was correct, the instance was infeasible and has been repaired; C-7 resolved — `y[s][t]` channelled and tested. 33 tests green |
| **Next step** | **Phase 3, blocked on a specification decision.** C-4 (a `v_i` and bounds for all seven soft criteria) and C-12 (S5 has weight 0.20 and no data) are the technical lead's, not the keyboard's. Nothing further can be encoded until they land |
| **Days used** | ~2 of 20. Phase 2 was budgeted 5 |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · 11 commits · the C-13 resolution is **uncommitted**, see "Resume from here" |
| **Blocked on** | Nothing. C-7 is a modelling decision that can be taken at the keyboard |

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

## Blockers, precisely

*Written 2026-07-29; C-6 below was resolved and implemented on 2026-07-30 - see the session log above.
Left in place because C-7's reasoning still stands and is referenced elsewhere.*

Two are decisions only the technical lead can make; the third is a modelling choice that can be made
at the keyboard.

### ~~Blocks *finishing* Phase 2~~ — **C-13, RESOLVED 2026-07-30**

**The diagnosis recorded here was wrong.** It read: "room-assignment symmetry makes H1–H12 hard to
solve in practice, even though no bug has been found." There was no search-performance problem. The
*instance* had no solution: 80 two-period `Lab_Info` sessions against 66 available two-period windows,
24 `Lab_Sciences` against 22. The model was correct throughout and now solves in ~3 s on the repaired
instance. Full account in `docs/open-questions.md` under C-13, and in the fourth-continuation session
log above.

### ~~Blocks the *objective* inside Phase 2~~ — **C-7, RESOLVED 2026-07-30**

The rule linking `start[s]` and `y[s][t]` across a 2-period duration appeared in none of the three
documents. It is now written, implemented (`solver/occupancy.py`) and tested: start indicators
`x[s,t₀]`, an `exactly_one` over them, and `y[s,t]` as the sum of the starts that would cover `t`.
Measured 4,720 + 5,328 = 10,048 variables, built on demand because they cost the feasibility solve
2.5×. Full reasoning in `docs/open-questions.md` under C-7.

**One half of C-7 remains open and belongs to C-4**: the objective's auxiliary variables (first/last
occupied period per group-day, reified gap indicators) still cannot be counted, because how many there
are follows from criterion formulas that do not exist yet.

### Blocks Phase 3

**C-4 — no soft criterion has a measurement formula.** All seven have codes, names and weights and
none has a definition of `v_i`. It feeds the score, the contributions, monotonicity, dominance and the
weight learning. Each also needs its `min_i`/`max_i` formula, which is one task per criterion, not two.
S6 additionally has a dead half: H5 already forbids a room smaller than its group, so "over-used" must
mean utilisation rate — the documents never say.

**C-12 — S5 carries weight 0.20 and has no input data.** `teacher_availability.csv` is a boolean and
all 157 rows are 0. Nothing expresses a *preferred* window, yet SRS §4.1 specifies a three-state grid.
⚠️ **This is C-5 in disguise**: if S5 measures identically zero, the teacher-favouring profile differs
by S3 alone, two candidates converge, duplicate removal drops one, and the three-candidate acceptance
test fails — for a reason nobody would look for.

### Decide at the keyboard, before the diagnosis run

**C-6 — RESOLVED 2026-07-30.** Only H1, H3, H7 and H12 are real postings a literal can attach to;
H2 and H11 are subsumed (no separate posting exists); H4/H5/H6/H8/H9/H10 are domain restrictions
(nothing posted at all, by construction). Implemented in `solver/constraints/`, not just decided.

---

## Next, in order

1. ~~Loader~~ - done, committed (`2c9c356`).
2. ~~Model H1-H12, H12 bug fixed~~ - done, committed (`0f9253e`, `c91a346`, `c1be462`).
3. ~~Decide C-13~~ - **resolved 2026-07-30**: the instance was infeasible, not the model slow. Repaired
   by re-typing three classrooms as laboratories; task 11 passes in ~3 s.
4. ~~Decide C-7~~ - **resolved and implemented 2026-07-30**: start-indicator channelling in
   `solver/occupancy.py`, built on demand. **Phase 2's modelling is complete.**
5. **Decide C-12 and C-4**, then scoring - Phase 3. This is now the immediate next step, and it is a
   specification decision for the technical lead, not a keyboard one: seven criteria need a `v_i` and a
   `min_i`/`max_i` each, and the objective cannot be encoded until they exist. The variables it will
   read (`x[s,t₀]`, `y[s,t]`) are built and tested.
6. **Port the five verifications into the application** as FR-12. The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API. ⚠️ **Port the contiguity bound, not just the period bound** — the
   period bound alone is what let C-13 through, and shipping it alone would put the same blind spot in
   the product.

Persistence can wait: the solver can read the CSVs through the loader, and PostgreSQL is only needed
once runs, candidates and publication have to survive a restart.

---

## Phases — increment 1, 20 working days

| Phase | Work | Days | Milestone |
|---|---|---|---|
| 1 | Needs, specification, source evaluation, instance verification | 3 | Instance verified, sources evaluated, scope fixed |
| 2 | Modelling H1–H12, first valid timetable | **5** | A timetable without conflict on the instance |
| 3 | Profiles, portfolio, score, ranking, decomposition, recommendation catalogue, regeneration, validation on published instances | 3 | Several candidates produced, ordered, and a difference decomposed |
| 4 | Availability grid, generation screen, comparison screen, views | 4 | Complete path from declaring availability to publication |
| 5 | Pre-solve verification, diagnosis run, authentication, rights, run record | 2 | An infeasible instance produces a report naming the rules in conflict |
| 6 | Tests, documentation, presentation | 3 | Application demonstrable, documents complete |

Phase 2 gets the largest share because it carries the most uncertainty.

**Increment 2, conditional on remaining time:** examination session (4 d), weight adjustment (3 d).
Natural-language constraint entry is **not undertaken** — it would require a solver-validation harness
that does not fit the project (see `docs/ai-integration.md`).

---

## Order of scope reduction, if the work runs late

Decided in advance, so the decision is not taken under pressure:

1. The assistant's **report** is abandoned — explanations and answers kept.
2. **Weight adjustment** is abandoned — catalogue weights kept.
3. The **examination session** is reduced to placement under X1–X4, without the spreading criterion.
4. The number of **quality criteria** in the score is reduced.
5. The number of **views** displayed is reduced.
6. **Rights management** is reduced to the separation between the person in charge and other users.

**Never reduced**, because they carry the demonstration that the application works and that its results
can be justified: the engine, pre-solve verification, diagnosis of infeasible instances, the score with
its decomposition, and validation on the published instances.

---

## Live risks

| Risk | Effect | Handling |
|---|---|---|
| **~2.5 unbudgeted assistant days** (C-1) | ≈12% overrun on 20 days | Confirmed, not contingent. Release valve is reduction step 1 |
| **91% laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and, as C-13 showed, an infeasible instance looks like a slow model** | Pre-analysis first, always, and read the *window* figure rather than the period figure. Re-check both whenever the instance changes |
| **A pre-analysis check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is attributed to the model. Cost three sessions on C-13 | Both bounds now checked in `verify_instance.py`. Any new check must state whether it is sufficient, and FR-12 must port both |
| **The cumulative reformulation and the warm-start were built for a problem that did not exist** | Two committed mechanisms (`cumulative_room_types`, `solver/warm_start.py`) are carried for a reason now known to be wrong. Both are correct and tested, neither is load-bearing: the model solves with the warm start off, and the greedy now reaches 218/218 in 0.04 s | **Not removed** — no evidence they harm anything, and both should earn their place once the objective makes the search non-trivial. **Whether the plain per-room encoding would now serve for every type is untested.** Re-evaluate when the objective lands; delete then if they still pay for nothing |
| **Objective encoding** | Auxiliary variables absent from the size estimate; second unknown after C-7 | 5 days budgeted to Phase 2 |
| **Deterministic-time calibration unmeasured** | The user-facing time limit is a guess | Calibrate in Phase 2, record below |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |
| ~~`uv` not installed~~ | — | **Resolved.** uv 0.12.0 installed; the whole toolchain runs |
| **Kaggle `students.csv` holds personal data** | 3,000 rows with names, emails, phones, addresses | Never load it beyond `student_id` + enrolment; never let such a field reach the assistant context |
| **C-12 × C-5 interaction** | If S5 measures zero, the teacher-favouring profile differs by S3 alone, candidates converge, and the "three candidates" acceptance test fails for an invisible reason | Resolve C-12 before Phase 3 |

---

## Housekeeping — three copies of the benchmark archives

| Location | Status |
|---|---|
| `data/reference/` | **Canonical.** Gitignored, documented by `PROVENANCE.md` |
| `dataset/` (repo root) | Duplicate. Gitignored by an explicit `/dataset/` rule — **safe to delete** |
| `..\dataset` (outside the repo) | The original. Safe to delete once you are happy with `data/reference/` |

⚠️ **Why the ignore rule matters.** `dataset/` was not covered by any pattern, so
all 161 files were staged for commit — including `students.csv` (3,000 rows of
names, e-mail addresses, phone numbers and postal addresses) and a 742 KB Windows
binary. Committing personal-data-shaped files is hard to undo once pushed. The
rule is now explicit; do not remove it.

## Measurements

Fill these in as they are taken. They are referenced from `CLAUDE.md` and `docs/constraint-model.md`.

| Measurement | Value | Taken on | Notes |
|---|---|---|---|
| **Toolchain** | **all green** | 2026-07-29 | 6/6 layer contracts kept · ruff clean · mypy strict clean on 20 files · frontend `tsc` clean · instance verified |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| Deterministic time → wall clock, reference instance | **not a clean ratio under `num_workers=0`** | 2026-07-30 | `max_deterministic_time=60` consumed 247.98 units before the 360s wall-clock ceiling stopped the run. Measured while searching an infeasible model, but the finding does not depend on that. Not urgent now — the repaired instance solves in ~0.2 deterministic units, far below any budget — and becomes urgent again once the objective makes solves long enough to reach one |
| **First valid timetable** | **2.84–3.30 s wall · 0.13–0.21 deterministic** | 2026-07-30 | ✅ **Target < 60 s met with a wide margin.** Seven seeds (1, 7, 42, 123, 999, 2026, 31337), production defaults (`num_workers=0`, warm start on); all seven placed 218/218. Full pipeline: warm-start construction, solve, and independent re-verification of every hard constraint from the raw CSVs (`tests/integration/test_h1_h12.py`). Measured on the repaired instance — see C-13; the earlier `UNKNOWN` results were an infeasible instance, not a slow model |
| Portfolio of 3 candidates | *not yet measured* | — | Target < 5 min |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| **Effective `y[s][t]` count after pruning** | **5,328** of 6,104 | 2026-07-30 | 87.3% of the upper bound. Start indicators `x[s,t₀]`: **4,720**. Together 10,048 variables (C-7) |
| **Cost of building the C-7 accounting** | **2.9–4.1 s → 7.6–8.0 s** | 2026-07-30 | Same configuration, three seeds; deterministic time 0.4–1.9 → ~6.1. Why `build_occupancy()` is called on demand and not by the feasibility solve |

### Measured on the instance, 2026-07-30 (after the C-13 repair)

Two bounds, because **the period bound alone is misleading** — that is what hid C-13. A two-period
session needs two *consecutive* open periods inside one day, so what a room really offers is
`Σ floor(L/2)` over its contiguous runs: **11 two-period windows a week**, not 28 periods.

| Room type | Rooms | Periods used / available | Period occupancy | 2-period windows used / offered | **Binding** |
|---|---|---|---|---|---|
| Amphi | 2 | 32 / 56 | 57.1% | — (no 2-period sessions) | — |
| Salle | 7 | 82 / 196 | 41.8% | — | — |
| **Lab_Info** | **8** | 160 / 224 | 71.4% | **80 / 88** | **90.9% ← tightest point** |
| Lab_Sciences | 3 | 48 / 84 | 57.1% | 24 / 33 | 72.7% |

`Lab_Info` has **8 spare two-period windows in the whole week**. Withdrawing one computer laboratory
removes 11 and makes the instance infeasible again. Re-run `scripts/verify-instance.ps1` after any
change to the instance — it now checks both bounds and fails, naming the shortfall, if either is
violated.

**For comparison, the original mix and why it read as feasible:** `Lab_Info` 6 rooms, 160 / 168
periods = **95.2 %** — comfortable — against 80 sessions needing 66 windows, **short by 14**.
`Lab_Sciences` 2 rooms, 48 / 56 = 85.7 %, against 24 needing 22, **short by 2**. The period figure was
never wrong arithmetically; it was answering a question that does not determine feasibility.

---

## Acceptance criteria — increment 1

Track these as they are met; the project is accepted requirement by requirement.

- [x] **No hard-constraint violation on the reference instance** — met 2026-07-30. Every one of H1–H12
      re-derived from the raw CSVs and checked against the returned placements, independently of
      CP-SAT's own status (`tests/integration/test_h1_h12.py`)
- [ ] At least three candidates, each with its overall score and sub-scores *(see C-5)*
- [ ] The sum of displayed contributions equals the score difference, to display precision
- [ ] Two runs with the same data, weights and seed produce the same candidates in the same order
- [ ] An instance without a solution produces a report naming the rules in conflict
- [ ] A teacher account obtains only its own availability and timetable
- [ ] Closing a half-day in configuration removes those slots from every timetable, **with no code change**
- [ ] The availability grid is filled in under 5 minutes without training
- [ ] Every published timetable traces back to its run, seed and weights
