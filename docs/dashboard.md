# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-08-05. Phase 6 is UNDER WAY — M0 done: C-5 and C-14 resolved by project-owner
decision, which is what unblocks the acceptance tests.** Phase 5 is COMPLETE — all six milestones, closing audit passed. FR-12 runs inside the application
(the five checks, **both** bounds, displayed as figures rather than ticks) and FR-8's diagnosis run
exists (rule withdrawal over plain subset solves, `INFEASIBLE → DIAGNOSING → DIAGNOSED`, conflict
report screen).

⚠️ **M2 raised C-17, and it is now RESOLVED on measurement.** The documented mechanism — enforcement
literals passed as assumptions — is correct at small scale and **inconclusive on this project's own
instance**: a literal takes `no_overlap` and `cumulative` out of presolve, so an infeasibility a plain
solve proves in **0.0 s** returned **`UNKNOWN` after 240 s**. Stage 3 now **withdraws one rule at a
time and solves plainly**, answering **`('H3',)`, minimal, in 1.9 s** on that instance. Two of the
three properties `docs/architecture.md` called "imposed by CP-SAT" changed with it — they were imposed
by the assumption mechanism.

⚠️ **The environment was re-verified from scratch on 2026-08-04, and one earlier decision was
reversed.** Docker is running, and **PostgreSQL 17 is reachable and writable through the repository's
own `Settings.database_url`** — so the SQLite fallback is dropped: the repository never chose SQLite
(its only trace is two lines inherited from GitHub's Python `.gitignore` template) and testing against
an engine the project does not ship would risk divergence. **M3 targets real PostgreSQL.**

One trap found while verifying it, now guarded: a native PostgreSQL 18 service owned port 5432, and
`docker compose up -d` **succeeded anyway** — container healthy, mapping shown, every host connection
reaching the *other* server. The host port is now configurable (default unchanged) and
`bootstrap.ps1` warns before starting. On this machine: `OPTIEDT_POSTGRES_PORT=5433`.

The other two scope decisions stand: publication is **in** Phase 5 as M5, and accounts come from a seed
command — see M4 and M5 below.

Phase 4 completed 2026-08-01, all six milestones and a closing audit: a teacher declares availability,
a run honours it, and the candidates are ranked, viewed four ways and compared with contributions that
add up by hand. Two questions were decided along the way — **C-12(a)** resolved (two-state grid) and
**C-14** deferred (**no** dominance signal shipped rather than one that can never fire).

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **75 % of budgeted effort** — Phases 1–4 delivered, 15 of 20 days budgeted; Phase 5 is under way and its 2 days are not yet counted. By *delivered product*: **6 of 9 acceptance criteria** met, **16 of 25 requirements under way, 0 finished**, because a requirement is `✓` only once a user can reach it *and* it is tested end to end — most now wait on FR-11's authentication and Phase 6's acceptance tests rather than on a missing screen. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 6 — tests, documentation, presentation. UNDER WAY**, M0 of 8. Phase 5 completed 2026-08-04 with six milestones and a closing audit. Milestone table in the Phase 6 block below |
| **Last completed phase** | **Phase 4 — COMPLETE 2026-08-01**, six milestones and a closing audit. Four screens (availability, generation, timetables, comparison) over ten `/api` endpoints, an in-process run executor, and the first frontend tests. Before it, Phase 3 delivered the criteria, scoring, ranking, decomposition, dominance, the objective, the portfolio, FR-16 and the ITC-2007 validation |
| **Milestone reached** | **Phase 5's, verified 2026-08-04.** The phase's stated milestone is *an infeasible instance produces a report naming the rules in conflict*, and M2 delivers it — ⚠️ with the limit C-17 measured: on an infeasibility CP-SAT cannot prove at all (the C-13 contiguity shape) the report is honestly **inconclusive**, and the pre-analysis is what names the resource. **Phase 4's milestone is also now complete**: it read "the complete path from declaring availability to publication", and publication landed in M5 — a candidate is published and traces back to its run, seed and weights across a restart |
| **Current goal** | Deliver Phase 5: an infeasible instance must produce a report naming the rules in conflict rather than a timeout, and every published timetable must trace back to its run, seed and weights |
| **Next task** | **Phase 6 M4 — the half-day closure (criterion 7, FR-9)**: close a half-day in configuration, re-solve, and assert no placement lands there *and* that no source file was touched. Then **M5** the instance generator, **M6** the demonstration script and the timed FR-2 walkthrough, **M7** documentation and the closing audit. ⚠️ **Criterion 5 needs a decision** — M3 measured it as met on one shape of infeasibility and not the other |
| **Branch** | `main` — ahead of `origin/main` by unpushed local commits. **No count is recorded here**, deliberately: `git rev-list --count origin/main..HEAD` |
| **Latest commit** | **Not recorded here** — it is stale the moment anything is committed. `git log -1 --oneline`. The durable fact is the last *pushed* commit, in the row below |
| **Repository status** | **No SHA and no commit count are recorded here. Derive them:** `git log -1 --oneline` · `git rev-parse --short HEAD` · `git rev-parse --short origin/main` · `git rev-list --count origin/main..HEAD` (0 means everything is pushed). Run `git fetch` first, or `origin/main` is only as fresh as your last one. ⚠️ **This row recorded a SHA and was wrong five times** — the fifth found on 2026-08-04, when it still named the Phase 4 audit commit and `origin/main` had moved two commits past it. Four of those five were *repaired by editing the value*, which is why there was a fifth: **a SHA cannot survive a push that does not touch this file, and a count cannot live in a file that commits change.** The values are therefore gone rather than corrected. The full record of each failure is in [`docs/history.md`](history.md) |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green across **nine** steps: **349 backend tests + 32 frontend**, **10/10 layer contracts** kept, mypy strict on 71 files, instance verified, **38 store-contract tests against real PostgreSQL**. Separately, `scripts/run-acceptance.ps1` green: **59 acceptance tests over nine requirements**, of which 26 solve for real. **6 of 9 acceptance criteria met** — M4 added the teacher's own data, M5 the published timetable's trace. The engine is validated on all 21 published ITC-2007 instances, and the whole path from declaring availability to comparing candidates is verified against the real solver |

```
Increment 1   ███████████████░░░░░  75 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ████████████████████  ✅ done
Phase 4  Web interface — grid, generation, comparison  ████████████████████  ✅ 6/6 milestones
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ████████████████████  ✅ 6/6 milestones
Phase 6  Tests, documentation, presentation            ░░░░░░░░░░░░░░░░░░░░  ⬜ not started  ← next
```

*Progress is measured in delivered phases against the 20-day increment-1 plan (Phase 1 = 3 d,
2 = 5 d, 3 = 3 d, 4 = 4 d, 5 = 2 d, 6 = 3 d). Phases 1–4 = 15 of 20 days budgeted.*

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **10/10 contracts kept**. The tenth (Phase 5 M3) keeps `api` off `db`, so the router layer never learns how anything is stored; verified to fire before being relied on, like the eighth and ninth. No layer edge has been weakened; the count has only ever gone up. The eighth (2026-07-31) keeps the ITC-2007 harness out of the product; the ninth (Phase 4 M1) keeps `api` off the solver. Both were verified to fire before being relied on |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 fully closed — accounting (`x[s,t₀]`, `y[s,t]`) built on demand, auxiliaries measured at **5,249**. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions; `engine.py` posts it — and builds occupancy at all — only when a criterion carries weight, so an all-zero profile is genuinely equivalent to a feasibility solve. **Deterministic budget calibrated 2026-07-30** — it binds exactly, per worker; 1 unit ≈ 4.8 s wall at one worker, ≈ 19 s at all sixteen. **`interleave_search = true` is set and is required for reproducibility** (C-16, ADR-011 amended); the warm start is withheld when an objective is posted, because it pinned all three profiles to one timetable |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance/**recommend** — FR-16). **The four properties the specification requires** (`docs/scoring-and-explanation.md`) all pass, verified by **ten** hypothesis tests in `tests/property/test_scoring_properties.py` — four specified, ten tests; the extra six cover edge cases the four imply but do not state |
| **Portfolio** | 🟢 `services/portfolio.py` — the only module importing both `solver` and `analysis`, which is what `services` is for. Defines the three profiles, divides the total budget between them, solves sequentially under one fixed seed, removes duplicate timetables and ranks the survivors under one weight vector. 16 unit tests pin the rules against a recording fake solver. Measured on the reference instance: **3 distinct candidates in 147–150 s**, reproducibly, total budget 90 (C-16) |
| **Persistence** | 🟢 **Built, Phase 5 M3 (FR-19).** PostgreSQL 17 behind the Protocols Phase 4 left in place — **no router changed**, which is what those Protocols were for. `db/models.py` normalises what `docs/domain-model.md` calls an entity (run, weights, candidate, placement, sub-score, check) and keeps two short ordered lists as JSON. Alembic was configured but never initialised; `migrations/env.py` now reads the URL from `Settings` so one connection string governs both the API and the migrations. **Verified by killing the API and reading a run back from a fresh process.** ⚠️ `persistence` is configuration, never detection: a store that fell back to memory when the database was unreachable would lose every run while looking healthy, which is the opposite of FR-19 |
| **API · frontend** | 🟢 **Complete for Phase 4.** Four screens — availability, generation, timetables, comparison — over ten endpoints. React shell with `react-router` and `@tanstack/react-query`; `features/generation` launches a run, polls it and renders the ranked candidates with all seven sub-scores; `features/timetable` shows a candidate by teacher, group, room and as room occupancy (FR-7, FR-18). **A group's view includes its ancestors' sessions** — a CM gathers the whole promotion, so a subgroup shown only its own sessions would display a week with holes its students do not have. ⚠️ **The frontend computes no score and decides no ranking**: rank order is the array order the API returns, and every figure shown arrives already computed (`docs/architecture.md`: the presentation layer may not "compute a score, decide an order"). It *does* arrange for display — grid axes, rooms alphabetically, and largest-remainder rounding so a contributions column adds up — which is what "display, filter, print" permits. Do not restate this as "the frontend computes nothing"; that is falsifiable by one grep and invites someone to conclude the rule is not meant seriously. The endpoints are `/api`, which `vite.config.ts` already proxies: the instance, FR-2's availability read/write, `POST /runs` → **202** with polling on `GET /runs/{id}`, and the candidate, comparison, dominance and recommendation reads. `tasks/executor.py` runs solves in-process on a **single-worker pool** (ADR-005) — one solve at a time, because each already uses every core. Both stores were **in memory** at Phase 4's close, behind Protocols; **Phase 5 M3 substituted database-backed ones and no router changed**, which is what those Protocols were for. A ninth import contract, `api ⇸ solver`, was added here and verified to fire; M3 added a tenth, `api ⇸ db` |
| **Pre-analysis** | 🟢 **Built, Phase 5 M1.** `preanalysis/verifications.py` — the five checks, **both** the period bound and the contiguity bound, run in every run's `PREANALYSIS` state against the instance about to be solved. Compared numerically against `data/verification/verify_instance.py` rather than trusted to agree with it. The C-13 regression is pinned by a test that reconstructs the pre-repair room mix. It imports `domain` and nothing else — the `preanalysis ⇸ solver` contract is what keeps it the instrument that tells an infeasible instance from a modelling regression |
| **Assistant** | ⬜ Scaffold only — interfaces, no bodies. Increment 1 by ADR-010, but **named in no phase's completion criteria**, which is exactly the ~2.5 unbudgeted days C-1 records. It was **not** part of Phase 4 and is not part of Phase 5's; schedule it explicitly or it stays homeless |
| **Validation** | 🟢 `scripts/run-checks.ps1` green, **nine steps**: layer boundaries (**10/10 contracts**) · ruff · format · mypy strict on 71 files · **263 fast backend tests** (including the 33 acceptance tests that need no solver) · **database tests against real PostgreSQL** · instance verification · frontend `tsc` · frontend tests. ⚠️ The database step **fails when no database was reached** — a forgotten `docker compose up -d`, which is actionable — and **skips** when Docker is absent, saying plainly that FR-19's persistence was not covered. ⚠️ **That failing half did not work until Phase 6 M1**: it checked the Docker *daemon*, so a stopped container let all 38 tests skip under a green tick. It now checks that tests actually **passed**, and the guard was verified to fire. `pytest` exit 5 is **no longer tolerated** (Phase 4 M1) — with 287 tests collected, allowing "collected nothing" would let a broken import pass as success. Separately, `scripts/validate-itc2007.ps1` runs the engine against the 21 published ITC-2007 instances — not in `run-checks` because a full sweep takes tens of minutes — and **`scripts/run-acceptance.ps1`** runs the 42 acceptance tests, whose solver-marked half takes about **7½ minutes** on two real portfolios |
| **Tests** | 🟢 **349 backend** (263 fast + 48 solver-marked + **38 database-marked**) **+ 32 frontend**. **Phase 6 M3 added 17** — 	est_fr08 (both infeasible shapes, end to end) and 	est_fr12 (the resource and the quantity named, including the C-13 contiguity bound). **Phase 6 M2 added 42** — the acceptance suite, `tests/acceptance/`, one file per requirement and each opening with the criterion it verifies: `test_fr03` (H1–H12 re-derived from the placements a user obtains through the API), `test_fr05`, `test_fr11` (real tokens, no dependency override), `test_fr13` (three distinct candidates, C-5's wording), `test_fr15`, `test_fr17` (C-14's reworded dominance), `test_fr19` (reproducibility *and* the publication trace — one requirement, two criteria). **Phase 6 M1 added 3 backend and 8 frontend** — the Pareto rule's new edge cases (`test_two_candidates_equal_on_every_criterion_dominate_neither`, and at catalogue weights the case C-14 turned on: beaten on all six weighted criteria, tied on S10) and `DominanceNotice.test.tsx`, which pins that an empty result reads as "checked, none found" rather than as a screen that does nothing. **M5 added 8 backend and 5 frontend** (`tests/integration/test_publication.py` — the trace checked against the RUN, not against a second copy of the seed; `TraceTable.test.tsx` — the whole weight vector on screen). **M4 added 25** (`test_rbac.py` against REAL tokens, `test_seed.py`). **M3 added 34** (`tests/integration/test_store_contract.py` — ONE suite run twice, over the in-memory store and over real PostgreSQL). **M2 added 13 backend** (`tests/unit/test_diagnosis.py` — the conflict set named exactly, against real CP-SAT, plus the guard that an enforcement literal genuinely relaxes its constraint) **and 6 frontend** (`ConflictReport.test.tsx` — the report never claims minimality, never reads as a repair list, and never shows an empty set as reassurance). **M1 added 32 backend and 5 frontend**: `tests/unit/test_preanalysis.py` (the five checks against hand-computable instances, and **the C-13 regression** — the pre-repair room mix must be caught by the contiguity bound), `tests/integration/test_preanalysis_matches_verifier.py` (the in-application checks against the standalone verifier, every figure re-derived from the raw CSVs) and `frontend/src/features/generation/PreAnalysisReport.test.tsx` (the figures reach the DOM; an empty report reads as "not run"). The frontend tests began in Phase 4 M5 (`vitest` + `@testing-library/react`) and `run-checks.ps1` runs them: they assert on **rendered** figures, which `tsc` cannot, and the acceptance criterion is about what is *displayed*. They caught a real rounding defect on their first run. Phase 4 also added `tests/unit/test_api_schemas.py` (the wire format: French enum literals, camelCase fields — the guard against the `RoomType` defect returning), `tests/unit/test_availability_api.py` (FR-2's replace-wholesale rule and the `SYNTHETIC`/`TEACHER` distinction), `tests/unit/test_run_lifecycle.py` (the state machine, including that `DIAGNOSING` is reachable only from `INFEASIBLE`) and `tests/integration/test_api_runs.py` (the run endpoints against a **fake solver**, so they stay in the fast suite and carry no timing assumption — the test waits on the executor's Future). Phase 3's 125 are unchanged. New in Phase 3: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended), `tests/unit/test_itc2007_cost.py` and `tests/integration/test_itc2007_validation.py` (ITC-2007's rules against hand-computed values, and against seven solutions the archive publishes) |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification. ⚠️ **It does not block the Phase 6 acceptance suite** — neither the nine criteria nor `testing-strategy.md` §4's table names any of the four. Corrected 2026-08-05 | The `✓` of FR-6, FR-10, FR-18 | Technical lead |
| **C-15** | The objective weights raw violation counts of incomparable scale, so "teacher-favouring" favours only S5, not S3. **Deferred by decision 2026-07-30** — recorded, objective unchanged. The comparison screen sidesteps it by showing measured sub-scores and making **no claim about what a profile favours** | FR-13's `✓` | Technical lead |

**Resolved, do not reopen without new evidence:** C-1, C-2, C-3, C-6, C-7, C-8, C-11, C-13, **C-4,
C-12, C-16** (2026-07-30), **C-17, C-18** (2026-08-04), **C-5, C-14** (2026-08-05). ADR-011 was amended
rather than reversed: deterministic time bounds the *work*, `interleave_search` orders the *race*, and
both are required — see C-16.

✅ **C-5 resolved 2026-08-05 — the wording was clarified, the implementation left alone.** Duplicate
removal stays exactly as SRS Table 29 specifies; the acceptance criterion is tied to **the verified
reference instance at production settings** (three distinct candidates), and the general contract the
software makes on any instance is "at most three, duplicates removed". The test asserts **exactly
three**, not "at least two" — the measurement is 3 distinct / 0 removed, and a weaker assertion would
hide a regression rather than describe the product.

✅ **C-14 resolved 2026-08-05 — Pareto, and the signal moves off the top candidate.** Two independent
defects: the strict reading was silent exactly when a candidate was beaten on every *weighted*
criterion and tied on the zero-weight S10, and the "dominated **top** candidate" clause describes a
state the arithmetic forbids. ⚠️ **Switching to Pareto does not fix the second** — the unreachability
holds under Pareto too, because `TIE_BREAK_ORDER` covers all seven criteria. So the reading changed
*and* the signal moved to any candidate in the portfolio. `Recommendation.dominated_by` is still
provably `None` and is still kept dead visibly.

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
| ~~**In-memory stores, no authentication**~~ | ~~a restart loses every run; every endpoint is open~~ | **RESOLVED 2026-08-04, M3 and M4.** ⚠️ **Still not to be exposed**: `secret_key` defaults to `change-me-in-env`, a value published in this repository, so a deployment that does not set `OPTIEDT_SECRET_KEY` signs tokens anyone can forge. Authentication makes this safe to demonstrate, not safe to expose |
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

### Phase 6 — Tests, documentation, presentation · 🟡 **under way** · 3 days

**Purpose.** Acceptance requirement by requirement; the project is accepted that way.
**Completion criteria.** The nine acceptance criteria in `docs/status.md` all ticked; documents complete.
**Dependencies. All settled as of 2026-08-05 — nothing gates the acceptance tests.** **C-5** and
**C-14** were resolved by project-owner decision (wording clarified and implementation kept; Pareto
dominance with the signal moved off the top candidate). **C-9** was found not to block the suite at
all: neither the nine criteria nor `testing-strategy.md` §4's table names FR-6, FR-10, FR-17 or FR-18,
so the four requirements without a specification are also the four with no acceptance test to write.

| # | Milestone | State |
|---|---|---|
| **M0** | **C-5 and C-14 recorded** in `open-questions.md` with their reasoning, before any code | ✅ **done 2026-08-05** |
| **M1** | **C-14 implemented** — Pareto in `analysis/ranking.py`, the dominance signal Phase 4 withheld, the documentation that still describes the strict reading | ✅ **done 2026-08-05**, and it found a false green in `run-checks.ps1` |
| **M2** | **Acceptance harness + the six met criteria**, one file per FR, driven through the API so each proves *reachable* capability | ✅ **done 2026-08-05** — 42 tests, and one of them was wrong before the product was |
| **M3** | **FR-8 + FR-12 acceptance tests** — an infeasible instance to `DIAGNOSED`. **Settles whether criterion 5 is met**, see below | ✅ **done 2026-08-05** — 17 tests, and the answer is *on one shape, not the other* |
| **M4** | **FR-9 acceptance test** — a half-day closed in configuration, no source file touched | ⬜ |
| **M5** | **Instance generator** (`data/generator/`) | ⬜ |
| **M6** | **Demonstration script + the FR-2 walkthrough protocol** | ⬜ |
| **M7** | **Documentation, traceability, closing audit** | ⬜ |

**Scope decisions taken by the project owner on 2026-08-05, before any code:**

1. **The assistant and regeneration are deferred, and the deferral is written down.** FR-22, FR-23,
   FR-24 and FR-25 stay `—`; `assistant/` stays scaffold-only. ADR-010 commits them to increment 1 and
   PPM Table 8 budgets them into no phase — that is C-1, and Phase 6 is not where it is absorbed
   silently. `testing-strategy.md` §4's four assistant rows are marked out of scope with the reason.
   FR-23 additionally needs H10's dormant gap filled (item 9 of `status.md`'s "Next, in order").
2. **The generator reproduces every documented figure, and `data/instance/` is not touched.**
   Byte-exact reproduction is **not achievable** — 425 student names and 218 teacher assignments came
   from a random stream that was never committed, so a "generator" emitting them exactly would be a
   copy wearing a generator's name. ADR-008 and C-11 record what is and is not achieved.
3. **The presentation deliverable is a reproducible demonstration script** in `docs/`, each step
   stating its expected result so a failed demonstration is visible rather than improvised around.

**Also lands here.** The **instance generator** (`data/generator/`), a stated PPM §10 deliverable that
does not exist — item 10 of `docs/status.md`'s "Next, in order". It must reproduce *the* documented
instance, not merely a valid one (ADR-008). And the **timed FR-2 walkthrough**: the availability grid
is built, but "filled in under 5 minutes without training" is about a person and no automated check
stands in for it.

**Status.** M0–M3 done. **Six of nine** acceptance criteria are met — Phase 5 added **two**: a
teacher's own data (M4) and a published timetable's trace (M5). M2 did not tick a new one; it turned
the six from *measured once by hand* into *checked by the suite*, which is what Phase 6 owes them.
**M3 measured criterion 5 and the answer needs a decision** — see below.

#### M3 — what landed, 2026-08-05, and the question it settles

`tests/acceptance/test_fr08.py` and `test_fr12.py`, **17 tests**, both infeasible shapes exercised end
to end through the API. Measured rather than assumed:

| Shape | Pre-analysis | Stage 2 | Stage 3 |
|---|---|---|---|
| **Area** — 4 of 8 computer laboratories, 160 periods against 112 | fails, names `Lab_Info` **short by 48 periods / 36 windows** | `INFEASIBLE` | **`DIAGNOSED`, `('H3',)`, minimal, conclusive** |
| **Contiguity** — the pre-C-13 mix | fails, names `Lab_Info` **short by 14 windows**, `Lab_Sciences` by 2 | `UNKNOWN` → raises → **`FAILED`** | never reached |

⚠️ **So criterion 5 — "an instance without a solution produces a report naming the rules in conflict" —
is met on infeasibilities CP-SAT can prove, and not met in general.** On the contiguity shape the user
gets no rule codes at all. What they do get is a `FAILED` run carrying *"neither a solution nor a proof
of infeasibility within the time given"* and a pre-analysis report naming the resource and the
shortfall — which is **not a timeout**, and is the phase's stated purpose, but is not the criterion's
stated wording.

**The tick is a project-owner decision, not a keyboard one**, and it is the same class as C-5: an
accepted criterion whose wording does not fit what was built. It is left **unticked** until decided,
because that is the conservative reading. The evidence is above and in the tests, which encode **both**
outcomes — writing only the area case would have let the suite report a capability the product does not
have.

⚠️ **The contiguity test does not prove "CP-SAT can never do this".** It runs at one budget, and one
budget cannot support a claim about every budget. What supports that claim is the recorded measurement
(480 s → `UNKNOWN`, C-13) and C-17's re-measurement. The test's own docstring says so.

#### M2 — what landed, 2026-08-05

`backend/tests/acceptance/`, **42 tests over seven requirements** — FR-3, FR-5, FR-11, FR-13, FR-15,
FR-17, FR-19 — plus `scripts/run-acceptance.ps1`. Each file opens with the criterion it verifies,
quoted, so a reader can check the test against the promise rather than against the code.

- **Driven through the HTTP API, never through `services/` or `analysis/`.** A requirement is `✓` only
  once a user can *reach* it, so an acceptance test that called the layer directly would be asserting
  the arithmetic while skipping the claim.
- **Two engines, chosen per criterion.** Criteria about the ENGINE (no hard-constraint violation, three
  distinct candidates, two runs agreeing) take real CP-SAT at production settings and are marked
  `solver`; criteria about the APPLICATION (a candidate's score and sub-scores, contributions summing,
  who may read what) take a fake, because a 150-second solve would only make the suite too slow to run.
- **One portfolio, shared.** FR-3, FR-13 and FR-19's first run are the same session-scoped solve —
  three different questions about one run. FR-19 adds a second, because "repeat a run" is not a question
  one run can answer. **Two production solves, 7 min 35 s** for the whole solver-marked half.
- **25 of the 42 need no solver and run in `run-checks.ps1`**; the rest run in `run-acceptance.ps1`.

⚠️ **Two findings from writing them, and the first matters more than the tests do.**

**The H12 acceptance test was wrong, and the product was right.** It walked each session's ancestors and
marked them occupied, so two TP subgroups of one TD group appeared to clash — disjoint sets of students
who obviously can run at once. It failed on a correct timetable (`group 2 reached by S0007 and S0006`).
**That is the same wrong reading `solver/constraints/overlap.py` records as tried and rejected in Phase
2**, where it made the reference instance look genuinely infeasible. Arriving at it again, independently,
from the same plausible intuition, is why that module's docstring exists — and it is a reminder that a
failing acceptance test is a hypothesis about the product, not a verdict on it.

**A budget that "should" have worked did not, and the run said so.** FR-3's first revision used a total
deterministic budget of 9, reasoning from the recorded 2.8–3.3 s "first valid timetable". That figure is
a **feasibility** solve with every weight at zero. Through the portfolio the total is divided between
three profiles and each carries the objective, so 9 gives 3 per profile, CP-SAT returns `UNKNOWN`, and
the run lands in `FAILED` rather than presenting a non-answer as a timetable — the C-13 lesson working
in the product. The acceptance tests use production settings.

#### M1 — what landed, 2026-08-05

`analysis/ranking.py` now applies the standard Pareto rule; `features/comparison/DominanceNotice.tsx`
displays the signal Phase 4 withheld, portfolio-wide; and eleven documents and docstrings that
described the strict reading were corrected, including **ADR-002**, whose rationale paragraph described
a signal that could never fire. The decision ADR-002 records — dominance as a complement, never as the
order — is unchanged, which is why it is corrected rather than superseded.

⚠️ **M1's own validation run found a false green in `scripts/run-checks.ps1`, and it is the finding
worth carrying.** The database step checked whether the Docker **daemon** was up, never whether a
database was **reached**. With the daemon running and the container stopped — which is what this
machine was in, the container having exited 27 hours earlier — the session fixture skipped all 38
store-contract tests, pytest exited 0, and the step printed `[ok]`. `run-checks.ps1` reported **"All
checks passed" while FR-19's persistence was covered by nothing.**

The step now fails unless the run reports tests that actually passed, and **the guard was verified to
fire before being relied on** — the container was stopped, the build failed with the actionable
message, the container restarted, and the step went green over 38 real tests. Checking the *result*
rather than the container also covers the case a container check would miss: `docker compose up -d`
succeeds while another PostgreSQL owns the port, so a running container is not proof the suite reached
the database this repository ships.

**Three documents asserted the failing behaviour and none of them was true** — `dashboard.md`'s
Validation row, `status.md`'s, and `testing-strategy.md`'s marker table all said the step fails when
Docker is up but the container is not. A claim about a guard is not evidence the guard exists.

⚠️ **Corrected 2026-08-05: this block said Phase 5 added three, naming "the conflict report" among
them, and `status.md` said "three acceptance criteria moved".** Both were wrong and the arithmetic
pins it: four were met at Phase 4's close, M4 and M5 moved one each, which is the six this same
sentence reports. **Criterion 5 — "an instance without a solution produces a report naming the rules in
conflict" — is unticked, and deliberately so.** M2 built the diagnosis and it answers `('H3',)` in
1.9 s, but on the C-13 contiguity shape CP-SAT cannot prove the infeasibility at all and the report is
honestly *inconclusive*, so the criterion **as literally worded** is not met for every infeasible
instance. **M3 settles it** by writing the acceptance test that decides what "met" means here.

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
