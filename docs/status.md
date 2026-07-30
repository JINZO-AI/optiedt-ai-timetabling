# Status

**Increment 1 of 2 · Phase 2 in progress · blocked on one architecture decision, not broken.**
**Last updated 2026-07-30.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

---

## ▶ Resume from here — copy this to continue

> Resume OptiEDT Phase 2. Read `CLAUDE.md`, then `docs/status.md` in full (all three "Session log —
> 2026-07-30" entries), then `docs/open-questions.md`'s C-13 — do not open the PDFs.
>
> The loader, variables, and all 12 constraint builders — including the H12 ancestor-lineage fix and
> the C-13 cumulative-constraint reformulation — are committed and green (`c1be462`, `480061e`,
> `8f22e2b`; 24 tests, ruff, mypy, format, 7/7 import contracts, all pass with solver-marked tests
> excluded from the default fast path). The integration test is committed too
> (`backend/tests/integration/test_h1_h12.py`, `@pytest.mark.solver`). **Do not redo any of this work.**
>
> **Task 11 is still blocked, and the chosen fix (C-13 option 3, reformulate room assignment as a
> cumulative constraint) did not resolve it on its own.** Measurements, most recent first:
>
> | Configuration | Budget | Result |
> |---|---|---|
> | Cumulative reformulation, tuned, 480s | 480s wall | `UNKNOWN`, 405,301 conflicts, 2.42M branches |
> | Cumulative reformulation, tuned, 180s | 180s wall | `UNKNOWN`, 96,020 conflicts, 1.28M branches |
> | Cumulative reformulation, default parameters | 480s wall | `UNKNOWN` (via the integration test's own fixture) |
> | Per-room encoding, tuned, 480s (pre-reformulation) | 480s wall | `UNKNOWN`, 29 conflicts, 2.29M branches |
> | Per-room encoding, default parameters | 360s wall | `UNKNOWN`, 337,954 conflicts |
> | Room assignment alone (H3+H7, no teacher/hierarchy), per-room | 200s wall | `UNKNOWN`, 78,824 conflicts |
>
> The reformulation is real and correct (cut the room-assignment boolean count from thousands to 770 -
> only `Salle` still uses `assign[s,r]`; unit-tested; see `docs/constraint-model.md` and
> `solver/engine.py`'s labeller), but it did **not** meaningfully close the gap at a comparable budget.
> Two things are independently confirmed and should not be re-litigated:
>
> - **Pure time scheduling (H1+H12, no rooms at all) is fast** - confirmed `OPTIMAL` in the 2026-07-30
>   session, before this investigation started. The difficulty is specifically in the room dimension.
> - **No constraint subset, at any point across both sessions, has reproduced an instant `INFEASIBLE`.**
>   Every result has been `UNKNOWN` after real search effort, never the sub-0.1s signature the H12 bug
>   produced. This is still evidence of hardness, not of a remaining correctness bug.
>
> **What hasn't been tried yet, in rough order of promise:**
>
> 1. **A constructive greedy warm-start fed via `model.add_hint()`.** Build one feasible assignment by
>    hand (list-scheduling heuristic, outside CP-SAT) and hint it to the solver - CP-SAT is typically
>    fast at *verifying* a supplied assignment even when it's slow at *finding* one from scratch. Not
>    yet attempted this session.
> 2. **A genuinely large budget** (tens of minutes, not ~8) to see if the search converges at all, in
>    either direction, given enough time - only budgets up to 480s have been tried so far.
> 3. **Symmetry-breaking on `Salle`** (the one remaining per-room-encoded type) in case its partial
>    interchangeability (5-10 of 10 rooms) still contributes meaningfully - considered unlikely, since
>    `Salle` sits at only 29% occupancy, but not directly tested in isolation.
>
> **A second, independent finding, still unresolved**: under `num_workers=0` (parallel),
> `max_deterministic_time` does not tightly bound the search the way ADR-011 assumes for a
> single-worker budget - configured limits have consistently been exceeded before the wall-clock
> ceiling actually stops the run (e.g. a 60s deterministic budget consumed 247.98 deterministic-time
> units over 360s wall-clock). Flagged, not yet calibrated.
>
> **Before running any solve with `num_workers=0`, be aware it will use every CPU core** and can make
> even trivial shell commands stall for tens of seconds to minutes — budget for it, and always track
> background solves explicitly so you can stop them rather than leave them orphaned (see the incident
> in the first 2026-07-30 session log entry below).

---

## Where the project is

| | |
|---|---|
| **Current phase** | Phase 2 — H1-H12 built, fixed, reformulated per C-13 and committed (`c1be462`, `480061e`, `8f22e2b`); Phase 2's milestone ("a timetable without conflict on the instance") **still not reached** — the chosen reformulation was a real improvement but did not resolve it alone |
| **Next step** | Technical lead picks the next lever (warm-start hint, larger budget, or something else — see "Resume from here") |
| **Days used** | ~1.5 of 20. Phase 2 is budgeted 5 days |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · 9 commits, all green |
| **Blocked on** | A genuine engineering decision (see "Resume from here") — not an unresolved bug |

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

### Blocks *finishing* Phase 2 — new, 2026-07-30

**C-13 — room-assignment symmetry makes H1-H12 hard to solve in practice, even though no bug has been
found.** `Lab_Info` and `Lab_Sciences` are fully interchangeable room types at 95.2% and 85.7%
occupancy - the textbook hard case for CP-SAT's default search. Full detail, measurements and three
options in `docs/open-questions.md`. **This blocks task 11 and Phase 2's milestone directly** - it is
the one genuinely open item right now.

### Blocks the *objective* inside Phase 2

**C-7 — the `y[s][t]` channelling constraint is unwritten.** `y[s][t]` is up to 6,104 booleans and its
real job is soft-constraint accounting, not H7. **104 of the 218 sessions span two periods**, so
`y[s][t]` must mean *occupies* t, not *starts at* t — and the rule linking `start[s]`, `iv[s]` and
`y[s][t]` across a 2-period duration appears in none of the three documents. The auxiliary variables
the objective needs are also uncounted, so the stated model size is an underestimate.

*H1–H12 and a first conflict-free timetable do not need this.* Start there; C-7 bites when the
objective goes in.

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
3. **Decide C-13** (room-assignment symmetry - see `docs/open-questions.md`), implement the chosen
   option, then finish task 11 with a configuration that actually resolves. This is the immediate next
   step, ahead of everything below.
4. **Decide C-7**, then encode the objective.
5. **Decide C-12 and C-4**, then scoring - Phase 3.
6. **Port the five verifications into the application** as FR-12. The standalone checker at
   `data/verification/verify_instance.py` already has the logic; the in-application version reports
   structural risks through the API.

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
| **95% laboratory occupancy** | A modelling regression looks like an infeasible instance | Pre-analysis first, always. Re-check the figure whenever the instance changes |
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
| Deterministic time → wall clock, reference instance | **not a clean ratio under `num_workers=0`** | 2026-07-30 | `max_deterministic_time=60` consumed 247.98 deterministic-time units before the 360s wall-clock ceiling stopped the run. The parameter does not tightly bound parallel search the way ADR-011 assumes for one worker — needs further calibration, see C-13 |
| First valid timetable | **not yet reached** | 2026-07-30 | Room-assignment symmetry (C-13) makes H1-H12 hard to solve as currently encoded: `UNKNOWN` after 480s wall-clock with tuned parameters, no proof either way. Target < 60 s is now known to be unmet in the current encoding, not just unmeasured |
| Portfolio of 3 candidates | *not yet measured* | — | Target < 5 min |
| Diagnosis run on an infeasible instance | *not yet measured* | — | Single worker, no objective — expect it to be slow |
| Effective `y[s][t]` count after pruning | *not yet measured* | — | Upper bound 6,104 |

### Measured on the instance, 2026-07-29

| Room type | Demand / capacity | Occupancy |
|---|---|---|
| Amphi | 32 / 56 | 57.1% |
| Salle | 82 / 280 | 29.3% |
| **Lab_Info** | **160 / 168** | **95.2%** ← tightest point |
| Lab_Sciences | 48 / 56 | 85.7% |

Lab_Info has **8 spare room-periods in the whole week**. Withdrawing one computer laboratory removes 28
and makes the instance infeasible. Re-run `scripts/verify-instance.ps1` after any change to the
instance.

---

## Acceptance criteria — increment 1

Track these as they are met; the project is accepted requirement by requirement.

- [ ] No hard-constraint violation on the reference instance
- [ ] At least three candidates, each with its overall score and sub-scores *(see C-5)*
- [ ] The sum of displayed contributions equals the score difference, to display precision
- [ ] Two runs with the same data, weights and seed produce the same candidates in the same order
- [ ] An instance without a solution produces a report naming the rules in conflict
- [ ] A teacher account obtains only its own availability and timetable
- [ ] Closing a half-day in configuration removes those slots from every timetable, **with no code change**
- [ ] The availability grid is filled in under 5 minutes without training
- [ ] Every published timetable traces back to its run, seed and weights
