# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-08-04. Phase 5 is IN PROGRESS — M2 of 6 done.** FR-12 runs inside the application
(the five checks, **both** bounds, displayed as figures rather than ticks) and FR-8's diagnosis run
exists (assumption literals, `INFEASIBLE → DIAGNOSING → DIAGNOSED`, conflict report screen).

⚠️ **M2 raised C-17 and it needs a decision.** The documented stage-3 mechanism is correct — 14 tests
name exactly the guilty rule on small instances — and **inconclusive on this project's own instance**:
enforcement literals take `no_overlap` and `cumulative` out of presolve, so an infeasibility a plain
solve proves in **0.0 s** returns **`UNKNOWN` after 240 s** under assumptions. A deletion-based search
over plain subset solves answers `('H3',)` in **1.6 s**. M2 shipped the documented design and recorded
the limitation rather than redesigning silently.

Three scope decisions were taken before any code (publication is **in** Phase 5 as M5; persistence
tests run on SQLite with PostgreSQL proven by the migration; accounts come from a seed command) — see
M4 and M5 below.

Phase 4 completed 2026-08-01, all six milestones and a closing audit: a teacher declares availability,
a run honours it, and the candidates are ranked, viewed four ways and compared with contributions that
add up by hand. Two questions were decided along the way — **C-12(a)** resolved (two-state grid) and
**C-14** deferred (**no** dominance signal shipped rather than one that can never fire).

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **75 % of budgeted effort** — Phases 1–4 delivered, 15 of 20 days budgeted; Phase 5 is under way and its 2 days are not yet counted. By *delivered product*: **4 of 9 acceptance criteria** met, **13 of 25 requirements under way, 0 finished**, because a requirement is `✓` only once a user can reach it *and* it is tested end to end — most now wait on FR-11's authentication and Phase 6's acceptance tests rather than on a missing screen. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 5 — pre-analysis in-app, diagnosis, authentication, run record. IN PROGRESS — M2 of 6 done.** Pick up at **M3, the run record** — ⚠️ but read **C-17** first, which M2 raised |
| **Last completed phase** | **Phase 4 — COMPLETE 2026-08-01**, six milestones and a closing audit. Four screens (availability, generation, timetables, comparison) over ten `/api` endpoints, an in-process run executor, and the first frontend tests. Before it, Phase 3 delivered the criteria, scoring, ranking, decomposition, dominance, the objective, the portfolio, FR-16 and the ITC-2007 validation |
| **Milestone reached** | **Phase 4's, in the part that was buildable.** Verified 2026-08-01 end to end: a teacher declared unavailability on the grid, the declaration replaced the generated rows, a run honoured it (T001 never placed in a declared-unavailable slot across all three candidates), and the candidates were ranked, viewed four ways and compared with contributions that add up by hand. ⚠️ **Publication itself is not built** — the milestone's wording says "to publication", and that needs the run record and rights (FR-19, FR-11), which are Phase 5 |
| **Current goal** | Deliver Phase 5: an infeasible instance must produce a report naming the rules in conflict rather than a timeout, and every published timetable must trace back to its run, seed and weights |
| **Next task** | **Phase 5 M3 — the run record (FR-19)**: `db/` models, the first alembic migration, SQL-backed stores behind the Protocols Phase 4 left in place. ⚠️ **Read C-17 first** — M2 delivered stage 3 and measured it inconclusive at reference scale, and whether to change the mechanism is undecided. ⚠️ **Docker was not running** when Phase 5 began, so M3's PostgreSQL half needs it started. Phase 4 still leaves three things behind: **C-14** (no dominance signal), the **timed FR-2 walkthrough**, and the in-memory stores M3 replaces |
| **Branch** | `main` — ahead of `origin/main` by unpushed local commits. **No count is recorded here**, deliberately: `git rev-list --count origin/main..HEAD` |
| **Latest commit** | **Not recorded here** — it is stale the moment anything is committed. `git log -1 --oneline`. The durable fact is the last *pushed* commit, in the row below |
| **Repository status** | Last pushed: `origin/main` at [`8d1194b`](https://github.com/JINZO-AI/optiedt-ai-timetabling/commit/8d1194b), 2026-08-01 — the Phase 4 closing audit. **`HEAD` and `origin/main` were identical at that point, verified after a fetch.** ⚠️ **This row has now been wrong four times.** `0dc0078` (a *parent* commit) until 2026-07-31; `acf9aa0` with "9 commits ahead" until 2026-08-01, by which time eight of the nine were pushed; then "1 commit ahead", which the very commit correcting it made 2; then `bfe805a`, left stale by the push that followed. **A commit count cannot live in a file that commits change, and a SHA cannot survive a push that does not touch this file.** Re-derive both, always: `git rev-parse origin/main`, `git rev-list --count origin/main..HEAD` |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green across eight steps: **217 backend tests + 18 frontend**, **9/9 layer contracts** kept, mypy strict on 60 files, instance verified. **4 of 9 acceptance criteria met.** The engine is validated on all 21 published ITC-2007 instances, and the whole path from declaring availability to comparing candidates is verified against the real solver |

```
Increment 1   ███████████████░░░░░  75 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ████████████████████  ✅ done
Phase 4  Web interface — grid, generation, comparison  ████████████████████  ✅ 6/6 milestones
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ██████░░░░░░░░░░░░░░  🔄 2/6 milestones ← here
Phase 6  Tests, documentation, presentation            ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
```

*Progress is measured in delivered phases against the 20-day increment-1 plan (Phase 1 = 3 d,
2 = 5 d, 3 = 3 d, 4 = 4 d, 5 = 2 d, 6 = 3 d). Phases 1–4 = 15 of 20 days budgeted.*

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **9/9 contracts kept**. No layer edge has been weakened; the count has only ever gone up. The eighth (2026-07-31) keeps the ITC-2007 harness out of the product; the ninth (Phase 4 M1) keeps `api` off the solver. Both were verified to fire before being relied on |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 fully closed — accounting (`x[s,t₀]`, `y[s,t]`) built on demand, auxiliaries measured at **5,249**. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions; `engine.py` posts it — and builds occupancy at all — only when a criterion carries weight, so an all-zero profile is genuinely equivalent to a feasibility solve. **Deterministic budget calibrated 2026-07-30** — it binds exactly, per worker; 1 unit ≈ 4.8 s wall at one worker, ≈ 19 s at all sixteen. **`interleave_search = true` is set and is required for reproducibility** (C-16, ADR-011 amended); the warm start is withheld when an objective is posted, because it pinned all three profiles to one timetable |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance/**recommend** — FR-16). **The four properties the specification requires** (`docs/scoring-and-explanation.md`) all pass, verified by **ten** hypothesis tests in `tests/property/test_scoring_properties.py` — four specified, ten tests; the extra six cover edge cases the four imply but do not state |
| **Portfolio** | 🟢 `services/portfolio.py` — the only module importing both `solver` and `analysis`, which is what `services` is for. Defines the three profiles, divides the total budget between them, solves sequentially under one fixed seed, removes duplicate timetables and ranks the survivors under one weight vector. 16 unit tests pin the rules against a recording fake solver. Measured on the reference instance: **3 distinct candidates in 147–150 s**, reproducibly, total budget 90 (C-16) |
| **API · frontend · persistence** | 🟢 **Complete for Phase 4.** Four screens — availability, generation, timetables, comparison — over ten endpoints. React shell with `react-router` and `@tanstack/react-query`; `features/generation` launches a run, polls it and renders the ranked candidates with all seven sub-scores; `features/timetable` shows a candidate by teacher, group, room and as room occupancy (FR-7, FR-18). **A group's view includes its ancestors' sessions** — a CM gathers the whole promotion, so a subgroup shown only its own sessions would display a week with holes its students do not have. ⚠️ **The frontend computes no score and decides no ranking**: rank order is the array order the API returns, and every figure shown arrives already computed (`docs/architecture.md`: the presentation layer may not "compute a score, decide an order"). It *does* arrange for display — grid axes, rooms alphabetically, and largest-remainder rounding so a contributions column adds up — which is what "display, filter, print" permits. Do not restate this as "the frontend computes nothing"; that is falsifiable by one grep and invites someone to conclude the rule is not meant seriously. The endpoints are `/api`, which `vite.config.ts` already proxies: the instance, FR-2's availability read/write, `POST /runs` → **202** with polling on `GET /runs/{id}`, and the candidate, comparison, dominance and recommendation reads. `tasks/executor.py` runs solves in-process on a **single-worker pool** (ADR-005) — one solve at a time, because each already uses every core. Both stores are **in memory** behind Protocols; Phase 5 substitutes database-backed ones with no router change. A ninth import contract, `api ⇸ solver`, was added and verified to fire. PostgreSQL is not needed until runs must survive a restart |
| **Pre-analysis** | 🟢 **Built, Phase 5 M1.** `preanalysis/verifications.py` — the five checks, **both** the period bound and the contiguity bound, run in every run's `PREANALYSIS` state against the instance about to be solved. Compared numerically against `data/verification/verify_instance.py` rather than trusted to agree with it. The C-13 regression is pinned by a test that reconstructs the pre-repair room mix. It imports `domain` and nothing else — the `preanalysis ⇸ solver` contract is what keeps it the instrument that tells an infeasible instance from a modelling regression |
| **Assistant** | ⬜ Scaffold only — interfaces, no bodies. Increment 1 by ADR-010, but **named in no phase's completion criteria**, which is exactly the ~2.5 unbudgeted days C-1 records. It was **not** part of Phase 4 and is not part of Phase 5's; schedule it explicitly or it stays homeless |
| **Validation** | 🟢 `scripts/run-checks.ps1` green, **eight steps**: layer boundaries (**9/9 contracts**) · ruff · format · mypy strict on 60 files · 195 fast backend tests · instance verification · frontend `tsc` · **frontend tests** (added Phase 4 M5). `pytest` exit 5 is **no longer tolerated** (Phase 4 M1) — with 217 tests collected, allowing "collected nothing" would let a broken import pass as success. Separately, `scripts/validate-itc2007.ps1` runs the engine against the 21 published ITC-2007 instances — not in `run-checks` because a full sweep takes tens of minutes |
| **Tests** | 🟢 **217 backend** (195 fast + 22 solver-marked) **+ 18 frontend**. **M2 added 14 backend** (`tests/unit/test_diagnosis.py` — the conflict set named exactly, against real CP-SAT, plus the guard that an enforcement literal genuinely relaxes its constraint) **and 6 frontend** (`ConflictReport.test.tsx` — the report never claims minimality, never reads as a repair list, and never shows an empty set as reassurance). **M1 added 32 backend and 5 frontend**: `tests/unit/test_preanalysis.py` (the five checks against hand-computable instances, and **the C-13 regression** — the pre-repair room mix must be caught by the contiguity bound), `tests/integration/test_preanalysis_matches_verifier.py` (the in-application checks against the standalone verifier, every figure re-derived from the raw CSVs) and `frontend/src/features/generation/PreAnalysisReport.test.tsx` (the figures reach the DOM; an empty report reads as "not run"). The frontend tests began in Phase 4 M5 (`vitest` + `@testing-library/react`) and `run-checks.ps1` runs them: they assert on **rendered** figures, which `tsc` cannot, and the acceptance criterion is about what is *displayed*. They caught a real rounding defect on their first run. Phase 4 also added `tests/unit/test_api_schemas.py` (the wire format: French enum literals, camelCase fields — the guard against the `RoomType` defect returning), `tests/unit/test_availability_api.py` (FR-2's replace-wholesale rule and the `SYNTHETIC`/`TEACHER` distinction), `tests/unit/test_run_lifecycle.py` (the state machine, including that `DIAGNOSING` is reachable only from `INFEASIBLE`) and `tests/integration/test_api_runs.py` (the run endpoints against a **fake solver**, so they stay in the fast suite and carry no timing assumption — the test waits on the executor's Future). Phase 3's 125 are unchanged. New in Phase 3: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended), `tests/unit/test_itc2007_cost.py` and `tests/integration/test_itc2007_validation.py` (ITC-2007's rules against hand-computed values, and against seven solutions the archive publishes) |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-17** | **The documented stage-3 mechanism is inconclusive at reference scale.** Enforcement literals defeat CP-SAT's presolve: 0.0 s to prove plainly, `UNKNOWN` after 240 s under assumptions; a deletion search over plain subset solves answers in 1.6 s. **NEW 2026-08-04, measured.** M2 shipped the documented design and recorded the limitation | FR-8 being useful on this instance; the acceptance criterion resting on it | Technical lead |
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |
| **C-14** | Dominance uses the strict reading ("improves on **every** criterion"); S10's zero weight makes ties common. **And the "dominated *top* candidate" signal both documents require is provably unreachable** — a dominated candidate cannot outscore its dominator, so it can never rank first. **Deferred 2026-08-01**: Phase 4 shipped **no** dominance signal rather than one that can never fire | FR-17's `✓`; Phase 6 acceptance; the wording of `scoring-and-explanation.md` | Technical lead **+ supervisor** |
| **C-15** | The objective weights raw violation counts of incomparable scale, so "teacher-favouring" favours only S5, not S3. **Deferred by decision 2026-07-30** — recorded, objective unchanged. The comparison screen sidesteps it by showing measured sub-scores and making **no claim about what a profile favours** | FR-13's `✓` | Technical lead |

**Resolved, do not reopen without new evidence:** C-1, C-2, C-3, C-6, C-7, C-8, C-11, C-13, **C-4,
C-12, C-16** (2026-07-30). ADR-011 was amended rather than reversed: deterministic time bounds the
*work*, `interleave_search` orders the *race*, and both are required — see C-16.

⚠️ **C-5 is still open, but the behaviour it worries about does not occur.** At production settings
the portfolio returns **3 distinct candidates, 0 duplicates removed**, reproducibly. C-5 is a conflict
in the specification's *wording* ("duplicates removed" vs "at least three candidates"), which a
favourable measurement cannot settle — but the acceptance test would pass today.

---

## Known risks

| Risk | Effect | Handling |
|---|---|---|
| **~2.5 unbudgeted assistant days** | ≈12 % overrun on 20 days | Confirmed, not contingent. Release valve is scope-reduction step 1 |
| **91 % laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and an infeasible instance looks like a slow model** | Pre-analysis first, always. Read the *window* figure, not the period figure |
| **A check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is blamed on the model. Cost three sessions on C-13 | Both bounds now checked. **FR-12's port must carry both** |
| ⚠️ **`interleave_search` is marked "Experimental" upstream** | Reproducibility — a written acceptance criterion — now rests on one OR-Tools parameter whose guarantee could change between releases. **And it already has one measured side effect**: `CpSolver.objective_value` can be reported 5–15 units above the objective at the solution actually returned, on solves that stop before proving optimality (found 2026-07-31 on ITC-2007 comp02/18/21) | **Pin the OR-Tools version.** `tests/integration/test_reproducibility.py` verifies reproducibility at production settings rather than trusting the docs; a failure there is blocking, not flaky. The objective-reporting quirk **affects nothing**, because no score, ranking or display reads `SolverOutput.cost` — the analysis layer recomputes from the placements, which is what the ban on `analysis → solver` forces. **Do not start ranking on `cost`.** Full account in ADR-011 |
| ~~**Deterministic-time calibration**~~ | ~~"the budget does not bind, ~11× over-run"~~ | **RESOLVED 2026-07-30 — the claim was false.** The budget binds *exactly*, per worker; `deterministic_time` reports the sum across workers and ~11 was the worker count on a 16-core machine. Calibrated figures in `docs/status.md`; correction in C-2 |
| **Raw-weight objective lets a large-scale criterion swamp a small one** | S5's raw value is ~100 (session count) while S3's is ~15 (idle periods). Inside teacher-favouring, S5 contributes 0.4×~80 ≈ 32 to the objective against S3's 0.3×~15 ≈ 4.5, so the profile is effectively S5-only. Measured: raising the budget improves S5 (101 → 72, better than balanced's 81) while S3 *degrades* (13 → 18) | The profile raises both weights exactly as documented, so this is not an implementation defect — it is a consequence of `minimise Σ(weight_i × violations_i)` using **raw** weights across criteria with incomparable scales. **"Teacher-favouring" does not currently favour teachers on S3.** Needs a decision (normalise the objective's weights, or set EMPHASIS per criterion); not resolved here |
| **S6 cannot be optimised for cumulative room types** | The CP-SAT objective only covers Salle (non-cumulative); Amphi/Lab_Info/Lab_Sciences rooms are chosen by a post-solve labeller the objective cannot see | Scored correctly after the fact regardless (`analysis/criteria.py`). Closing this needs `solver/variables.py` changes — out of scope this session |
| **`recommendations/translator.py` cannot build a full `SolverInput`** | `Run`/`Candidate` carry no instance reference, no base profile weights, no prior locks/exclusions | Returns a `RunOverride` (plain domain data) instead; a later layer (`services/`, Phase 4–5) must assemble the actual `SolverInput` |
| **On ITC-2007, cost quality is far from the published best on the larger instances** | Every timetable produced is *valid* — that is the claim `docs/testing-strategy.md` §1 makes first, and it holds 21 of 21. But at a minute or so per instance, CP-SAT is barely past feasibility on the big ones, and the costs are multiples of the published best | Expected, and the strategy document says so: **"the objective is not to beat published results."** Exact methods are known to trail metaheuristics tuned for this problem at short budgets. The *model* is demonstrably right — comp11 solved to **cost 0**, and comp01 reaches the published optimum of **5** given more search. Quote validity first and cost second, always with the budget |
| **Candidates are not shown as they are produced** | `architecture.md` stage 2 and ADR-005 both claim incremental visibility; `services/portfolio.py` returns the whole portfolio at the end, so the screen shows `SOLVING` for 105–150 s then everything at once | Found by the Phase 4 closing audit; both documents corrected. Closing it changes a **Phase 3** module's contract |
| **In-memory stores, no authentication** | A restart loses every run; every endpoint is open | Phase 4's documented position. FR-19 and FR-11 in Phase 5. **Not to be exposed beyond a development machine** |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |

---

## Roadmap — remaining phases

### Phase 3 — Score, ranking, portfolio, recommendations · ✅ **complete 2026-07-31**

**Purpose.** Turn one valid timetable into *several*, ordered, with the difference between any two
explained term by term. This is the half of the product that makes it defensible rather than merely
automatic.

**Completion criteria — all four met.**
- Three weight profiles produce candidates; each carries an overall score /100 and its sub-scores.
  ✅ **Met** — `services/portfolio.py`. On the reference instance it returns **3 distinct candidates,
  0 duplicates removed, in 147–150 s**, each scored /100 with its seven sub-scores. ⚠️ The profiles do
  not yet *steer* as their names promise — "teacher-favouring" improves S5 and not S3, for the
  documented reason (C-15, deferred by decision). The mechanism is complete; that calibration is not,
  and it is recorded rather than hidden.
- The displayed contributions **sum exactly** to the score difference, to display precision. ✅ **Met**
  at the code level — `analysis/ranking.py`'s `decompose()`, verified by
  `tests/property/test_scoring_properties.py::test_decomposition_is_exact` and, on three real portfolio
  candidates, agreeing to 9 decimal places. **The acceptance criterion itself was ticked in Phase 4 M5**,
  once the comparison screen existed and a test could read the rendered figures back out of the DOM.
- Dominance is detected and reported. ✅ **Met** — `DefaultRanker.dominance()`, property-tested.
- Two runs with the same data, weights and seed produce identical candidates in the same order.
  ✅ **Met at production settings** — via `interleave_search` (C-16, ADR-011 amended). Verified on
  candidate ids, order, placements, scores and sub-scores, and guarded at the production worker count
  by `tests/integration/test_reproducibility.py`. It was **not** true before 2026-07-30: three
  identical requests returned three different timetables, every one proving optimality.

**Dependencies.** ✅ **C-4** and **C-12** resolved 2026-07-30 — see `docs/open-questions.md` for the
formulas and reasoning. Phase 2 was otherwise a complete foundation.

**Status.** Complete. See "Phase 3 — complete 2026-07-31" below for the module-by-module account, the
two limitations carried forward (S6's cumulative-room-type gap, and regeneration's second half waiting
on Phase 5's run record), and the ITC-2007 results. Persistence of runs and candidates was never Phase
3 work — it is Phase 5's run record.

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

### Phase 5 — Pre-analysis in-app, diagnosis, auth, run record · 🔄 2 days budgeted · **in progress**

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
| **M2** | **Diagnosis run (FR-8)** — assumption literals on H1/H3/H7/H12, `INFEASIBLE → DIAGNOSING → DIAGNOSED`, conflict report screen | ✅ **done 2026-08-04**, ⚠️ **and it raised C-17** |
| **M3** | **Run record (FR-19)** — `db/` models, first alembic migration, SQL-backed stores behind the existing Protocols | ⬜ |
| **M4** | **Authentication and rights (FR-11)** — users, JWT, RBAC, teacher scoping, login screen | ⬜ |
| **M5** | **Publication + traceability** — closes *"every published timetable traces back to its run, seed and weights"* | ⬜ |
| **M6** | **Closing audit + documentation** | ⬜ |

**Three scope decisions taken before any code, on 2026-08-03.** All three were flagged rather than
assumed, because none is settled by the specification:

1. **Publication is IN Phase 5, as M5.** It appears in the phase's *purpose* sentence and in a written
   acceptance criterion, but in none of the four completion criteria — and Phase 4's milestone wording
   ("the complete path … to publication") already left it owed. Building it is the only way to tick
   that criterion.
2. **Persistence tests run on SQLite; PostgreSQL is proven by the migration and a manual pass.** One
   store-contract suite is parametrised over the in-memory and SQL implementations so it always runs
   in `run-checks.ps1`. The alternative — PostgreSQL-marked tests skipped when unreachable — would let
   green mean "not run" on a machine without Docker, which is the failure shape this project keeps
   catching. ⚠️ **Docker was not running when Phase 5 began**, which is what forced the question.
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

- ⚠️ **C-17, and it is the important one.** The documented mechanism works — 14 tests name exactly
  `('H1',)`, `('H12',)` or `('H3',)` on instances where one rule can be at fault — and is
  **inconclusive on this project's own instance**. Enforcement literals take `no_overlap` and
  `cumulative` out of presolve, so an area contradiction a plain solve proves in **0.0 s** returns
  **`UNKNOWN` after 240 s** under assumptions. A deletion-based search over plain subset solves answers
  `('H3',)` in **1.6 s**. M2 shipped the documented design and recorded the limitation rather than
  redesigning silently. **Read C-17 before relying on stage 3.**
- ⚠️ **The conflict set reads backwards by default.** It is an unsat core — *enforcing* those rules
  alone already admits no timetable — not a repair list. Measured: one teacher, one room, one slot,
  two sessions returns `('H1',)`, though relaxing H1 leaves H3 forbidding the same pair. The screen
  says "necessary, not necessarily enough" for exactly this reason.
- **`DIAGNOSED` does not mean a conflict was named.** It can be conclusive-and-empty (no *relaxable*
  rule explains it — the conflict is in the data) or inconclusive (no proof was found). Both are
  reported as such on screen; neither may read as "no problem found".

### Phase 6 — Tests, documentation, presentation · ⬜ 3 days

**Purpose.** Acceptance requirement by requirement; the project is accepted that way.
**Completion criteria.** The nine acceptance criteria in `docs/status.md` all ticked; documents complete.
**Dependencies.** All previous phases. **C-5**, **C-9** and now **C-14** must be settled before the
acceptance tests are written, or they will fail for reasons that are not defects. C-14 arrived here
when Phase 4 deferred it, and it carries a documentation change too: `docs/scoring-and-explanation.md`
still describes a dominance signal the arithmetic forbids, and **that wording needs the supervisor**.
**Also lands here.** The **instance generator** (`data/generator/`), a stated PPM §10 deliverable that
does not exist — item 9 of `docs/status.md`'s "Next, in order". It must reproduce *the* documented
instance, not merely a valid one (ADR-008). And the **timed FR-2 walkthrough**: the availability grid
is built, but "filled in under 5 minutes without training" is about a person and no automated check
stands in for it.
**Status.** Not started. **Four of nine** acceptance criteria are met.

### Increment 2 — conditional on remaining time

Examination session (4 d) · weight adjustment from recorded comparisons (3 d). Natural-language
constraint entry is **not undertaken** — see `docs/ai-integration.md`.

---

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
of all three actions exist and are tested; turning an accepted recommendation into an actual new run
needs run/instance context that arrives with Phase 5's run record. That split is deliberate and
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

## Where to look for what

| You need | Read |
|---|---|
| Invariants, commands, conventions | `CLAUDE.md` |
| Detailed state, measurements, acceptance criteria | [`docs/status.md`](status.md) |
| What is undecided | [`docs/open-questions.md`](open-questions.md) |
| Why a past decision was taken | [`docs/decisions/`](decisions/) — 11 ADRs |
| What happened, session by session | [`docs/history.md`](history.md) — archive, read only for forensics |
| "Is FR-15 built?" | [`docs/requirements-traceability.md`](requirements-traceability.md) |
| How the engine is validated, and against what | [`docs/testing-strategy.md`](testing-strategy.md) |
| Everything else | The table in `CLAUDE.md` |
