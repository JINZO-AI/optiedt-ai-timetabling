# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-08-06. Phase 6 is COMPLETE — all eight milestones and a closing audit.**

⚠️ **Phase 6 is complete and INCREMENT 1 IS NOT.** Eight of nine acceptance criteria are met (the
ninth is a timed walkthrough needing a person), the acceptance suite covers ten requirements, and the
instance generator is delivered. But **FR-22, FR-24, FR-25** (the assistant) and **FR-23**
(regeneration) are committed to increment 1 by **ADR-010** and are allocated to **no phase** of the
20-day plan. That is **C-1**, recorded since 2026-07-29 and never scheduled. The plan's 20 days are
now exhausted. **The remaining work needs a home and that decision is the project owner's** — it is
not taken here, and neither ADR-010 nor the roadmap has been modified. Phase 5 is COMPLETE — all six milestones, closing audit passed. FR-12 runs inside the application
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
| **Current phase** | **Phase 6 — tests, documentation, presentation. COMPLETE 2026-08-06**, all eight milestones and a closing audit. ⚠️ **Increment 1 is not complete with it** — see the header. Milestone table in the Phase 6 block below |
| **Last completed phase** | **Phase 4 — COMPLETE 2026-08-01**, six milestones and a closing audit. Four screens (availability, generation, timetables, comparison) over ten `/api` endpoints, an in-process run executor, and the first frontend tests. Before it, Phase 3 delivered the criteria, scoring, ranking, decomposition, dominance, the objective, the portfolio, FR-16 and the ITC-2007 validation |
| **Milestone reached** | **Phase 6's, 2026-08-06.** Its stated milestone is *"application demonstrable, documents complete"* — `docs/demonstration.md` is the executable script and the closing audit is done. ⚠️ **The one thing Phase 6 could not close is criterion 9**, the timed availability-grid walkthrough: it is about a person and needs a teacher who has not seen the screen (demonstration.md §2) |
| **Current goal** | ⚠️ **None — there is no current phase.** All six phases of the plan are delivered and its 20 days are spent. The next action is a **decision, not code**: FR-22, FR-24, FR-25 (the assistant) and FR-23 (regeneration) are committed to increment 1 by ADR-010 and were allocated to no phase (**C-1**). Where that work goes is the project owner's call |
| **Next task** | ⚠️ **Do not start code. Ask first.** Read the Increment 1 completion report in this file's Phase 6 block, then put the choice to the project owner: **(A)** a Phase 7 for the assistant and regeneration, **(B)** move them to increment 2, or **(C)** a scope correction. **(A) is the recommended option** — it is the only one that changes a schedule rather than a delivered commitment, and the only one that gives FR-23 a home. ⚠️ **ADR-010, the roadmap and the phase table must not be modified without that approval** |
| **Branch** | `main` — ahead of `origin/main` by unpushed local commits. **No count is recorded here**, deliberately: `git rev-list --count origin/main..HEAD` |
| **Latest commit** | **Not recorded here** — it is stale the moment anything is committed. `git log -1 --oneline`. The durable fact is the last *pushed* commit, in the row below |
| **Repository status** | **No SHA and no commit count are recorded here. Derive them:** `git log -1 --oneline` · `git rev-parse --short HEAD` · `git rev-parse --short origin/main` · `git rev-list --count origin/main..HEAD` (0 means everything is pushed). Run `git fetch` first, or `origin/main` is only as fresh as your last one. ⚠️ **This row recorded a SHA and was wrong five times** — the fifth found on 2026-08-04, when it still named the Phase 4 audit commit and `origin/main` had moved two commits past it. Four of those five were *repaired by editing the value*, which is why there was a fifth: **a SHA cannot survive a push that does not touch this file, and a count cannot live in a file that commits change.** The values are therefore gone rather than corrected. The full record of each failure is in [`docs/history.md`](history.md) |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green across **nine** steps: **395 backend tests + 32 frontend**, **10/10 layer contracts** kept, mypy strict on 71 files, instance verified, **38 store-contract tests against real PostgreSQL**. Separately, `scripts/run-acceptance.ps1` green: **64 acceptance tests over ten requirements**, of which 31 solve for real. **6 of 9 acceptance criteria met** — M4 added the teacher's own data, M5 the published timetable's trace. The engine is validated on all 21 published ITC-2007 instances, and the whole path from declaring availability to comparing candidates is verified against the real solver |

```
Increment 1   ████████████████████  20 of 20 budgeted days  ⚠️ NOT complete - see the header

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ████████████████████  ✅ done
Phase 4  Web interface — grid, generation, comparison  ████████████████████  ✅ 6/6 milestones
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ████████████████████  ✅ 6/6 milestones
Phase 6  Tests, documentation, presentation            ████████████████████  ✅ 8/8 milestones
```

*Progress is measured in delivered phases against the 20-day plan (Phase 1 = 3 d, 2 = 5 d, 3 = 3 d,
4 = 4 d, 5 = 2 d, 6 = 3 d). All six are delivered: 20 of 20 days.*

⚠️ **The bar says 20 of 20 and increment 1 is still not complete, and that is the point rather than a
rounding error.** The heading of `docs/status.md`'s phase table reads `Phases — increment 1, 20
working days`, which equates the six phases with the increment; ADR-010 commits FR-22, FR-23 and
FR-24 to increment 1 and the six phases name none of them. Both statements are in this repository and
they cannot both be right. **Nothing here decides it** — the evidence is in the Increment 1 completion
report and the decision is the project owner's.

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
| **API · frontend** | 🟢 **Complete for Phase 4, extended since.** ⚠️ *Corrected 2026-08-06: this row said `Four screens … over ten endpoints` and was describing Phase 4's close as if it were the present. There are now **seven screens** — availability, generation, timetables, comparison, sign-in, conflict report, publications — over **15 endpoints**. Derive both rather than editing them: `Get-ChildItem frontend/src/features -Directory` and `Select-String backend/src/optiedt/api/routers/*.py -Pattern '^@router\.'`.* React shell with `react-router` and `@tanstack/react-query`; `features/generation` launches a run, polls it and renders the ranked candidates with all seven sub-scores; `features/timetable` shows a candidate by teacher, group, room and as room occupancy (FR-7, FR-18). **A group's view includes its ancestors' sessions** — a CM gathers the whole promotion, so a subgroup shown only its own sessions would display a week with holes its students do not have. ⚠️ **The frontend computes no score and decides no ranking**: rank order is the array order the API returns, and every figure shown arrives already computed (`docs/architecture.md`: the presentation layer may not "compute a score, decide an order"). It *does* arrange for display — grid axes, rooms alphabetically, and largest-remainder rounding so a contributions column adds up — which is what "display, filter, print" permits. Do not restate this as "the frontend computes nothing"; that is falsifiable by one grep and invites someone to conclude the rule is not meant seriously. The endpoints are `/api`, which `vite.config.ts` already proxies: the instance, FR-2's availability read/write, `POST /runs` → **202** with polling on `GET /runs/{id}`, and the candidate, comparison, dominance and recommendation reads. `tasks/executor.py` runs solves in-process on a **single-worker pool** (ADR-005) — one solve at a time, because each already uses every core. Both stores were **in memory** at Phase 4's close, behind Protocols; **Phase 5 M3 substituted database-backed ones and no router changed**, which is what those Protocols were for. A ninth import contract, `api ⇸ solver`, was added here and verified to fire; M3 added a tenth, `api ⇸ db` |
| **Pre-analysis** | 🟢 **Built, Phase 5 M1.** `preanalysis/verifications.py` — the five checks, **both** the period bound and the contiguity bound, run in every run's `PREANALYSIS` state against the instance about to be solved. Compared numerically against `data/verification/verify_instance.py` rather than trusted to agree with it. The C-13 regression is pinned by a test that reconstructs the pre-repair room mix. It imports `domain` and nothing else — the `preanalysis ⇸ solver` contract is what keeps it the instrument that tells an infeasible instance from a modelling regression |
| **Assistant** | ⬜ Scaffold only — interfaces, no bodies. Increment 1 by ADR-010, but **named in no phase's completion criteria**, which is exactly the ~2.5 unbudgeted days C-1 records. It was **not** part of Phase 4 and is not part of Phase 5's; schedule it explicitly or it stays homeless |
| **Validation** | 🟢 `scripts/run-checks.ps1` green, **nine steps**: layer boundaries (**10/10 contracts**) · ruff · format · mypy strict on 71 files · **300 fast backend tests** (including the 33 acceptance tests that need no solver) · **database tests against real PostgreSQL** · instance verification · frontend `tsc` · frontend tests. ⚠️ The database step **fails when no database was reached** — a forgotten `docker compose up -d`, which is actionable — and **skips** when Docker is absent, saying plainly that FR-19's persistence was not covered. ⚠️ **That failing half did not work until Phase 6 M1**: it checked the Docker *daemon*, so a stopped container let all 38 tests skip under a green tick. It now checks that tests actually **passed**, and the guard was verified to fire. `pytest` exit 5 is **no longer tolerated** (Phase 4 M1) — with 287 tests collected, allowing "collected nothing" would let a broken import pass as success. Separately, `scripts/validate-itc2007.ps1` runs the engine against the 21 published ITC-2007 instances — not in `run-checks` because a full sweep takes tens of minutes — and **`scripts/run-acceptance.ps1`** runs the 42 acceptance tests, whose solver-marked half takes about **7½ minutes** on two real portfolios |
| **Tests** | 🟢 **395 backend** (300 fast + 57 solver-marked + **38 database-marked**) **+ 32 frontend**. **Phase 7 M1 added 13** — 9 in `tests/unit/test_solver_variables.py` (H10 narrows the start domain and the candidate rooms, touches no other session, and **cannot grant** a slot or room a hard rule forbids) and `tests/integration/test_h10_locks.py` (4 solver-marked: a lock survives a real solve, ten locks across room types survive together, and the limiting case — **all 218 placements locked returns exactly the timetable given**). It replaced `test_locked_sessions_not_yet_supported`, which pinned the dormant behaviour. **Phase 6 M5 added 26** — `tests/unit/test_generator.py`, which runs the generator as a subprocess and holds its output to `verify_instance.py`, the same contract the committed files are held to. **M4 added 5** — 	est_fr09, which ticks acceptance criterion 7. **M3 added 17** — 	est_fr08 (both infeasible shapes, end to end) and 	est_fr12 (the resource and the quantity named, including the C-13 contiguity bound). **Phase 6 M2 added 42** — the acceptance suite, `tests/acceptance/`, one file per requirement and each opening with the criterion it verifies: `test_fr03` (H1–H12 re-derived from the placements a user obtains through the API), `test_fr05`, `test_fr11` (real tokens, no dependency override), `test_fr13` (three distinct candidates, C-5's wording), `test_fr15`, `test_fr17` (C-14's reworded dominance), `test_fr19` (reproducibility *and* the publication trace — one requirement, two criteria). **Phase 6 M1 added 3 backend and 8 frontend** — the Pareto rule's new edge cases (`test_two_candidates_equal_on_every_criterion_dominate_neither`, and at catalogue weights the case C-14 turned on: beaten on all six weighted criteria, tied on S10) and `DominanceNotice.test.tsx`, which pins that an empty result reads as "checked, none found" rather than as a screen that does nothing. **M5 added 8 backend and 5 frontend** (`tests/integration/test_publication.py` — the trace checked against the RUN, not against a second copy of the seed; `TraceTable.test.tsx` — the whole weight vector on screen). **M4 added 25** (`test_rbac.py` against REAL tokens, `test_seed.py`). **M3 added 34** (`tests/integration/test_store_contract.py` — ONE suite run twice, over the in-memory store and over real PostgreSQL). **M2 added 13 backend** (`tests/unit/test_diagnosis.py` — the conflict set named exactly, against real CP-SAT, plus the guard that an enforcement literal genuinely relaxes its constraint) **and 6 frontend** (`ConflictReport.test.tsx` — the report never claims minimality, never reads as a repair list, and never shows an empty set as reassurance). **M1 added 32 backend and 5 frontend**: `tests/unit/test_preanalysis.py` (the five checks against hand-computable instances, and **the C-13 regression** — the pre-repair room mix must be caught by the contiguity bound), `tests/integration/test_preanalysis_matches_verifier.py` (the in-application checks against the standalone verifier, every figure re-derived from the raw CSVs) and `frontend/src/features/generation/PreAnalysisReport.test.tsx` (the figures reach the DOM; an empty report reads as "not run"). The frontend tests began in Phase 4 M5 (`vitest` + `@testing-library/react`) and `run-checks.ps1` runs them: they assert on **rendered** figures, which `tsc` cannot, and the acceptance criterion is about what is *displayed*. They caught a real rounding defect on their first run. Phase 4 also added `tests/unit/test_api_schemas.py` (the wire format: French enum literals, camelCase fields — the guard against the `RoomType` defect returning), `tests/unit/test_availability_api.py` (FR-2's replace-wholesale rule and the `SYNTHETIC`/`TEACHER` distinction), `tests/unit/test_run_lifecycle.py` (the state machine, including that `DIAGNOSING` is reachable only from `INFEASIBLE`) and `tests/integration/test_api_runs.py` (the run endpoints against a **fake solver**, so they stay in the fast suite and carry no timing assumption — the test waits on the executor's Future). Phase 3's 125 are unchanged. New in Phase 3: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended), `tests/unit/test_itc2007_cost.py` and `tests/integration/test_itc2007_validation.py` (ITC-2007's rules against hand-computed values, and against seven solutions the archive publishes) |
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
C-12, C-16** (2026-07-30), **C-17, C-18** (2026-08-04), **C-5, C-14** (2026-08-05), **C-19, C-20,
C-21** (2026-08-06). ADR-011 was amended
rather than reversed: deterministic time bounds the *work*, `interleave_search` orders the *race*, and
both are required — see C-16.

✅ **C-19, C-20 and C-21 resolved 2026-08-06 by project-owner decision, before any Phase 7 code.**
C-19: `SolverInput` carries `frozenset[Placement]` instead of `frozenset[SessionId]`, so H10 stops being
dormant — a **Phase 2 contract change**, taken deliberately. C-20: regeneration assembles in
`services/regeneration.py`; the new run records its origin and its overrides, and overrides **compose**
so a second accepted recommendation does not silently discard the first. C-21: **no test calls a live
language model**, at any marker — a model's output is not fixed by a seed, and the grounding check is
better tested by a fake that fabricates a figure on demand than by a real one that may not.

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

**Status.** Complete. **Two limitations were carried forward and both are still true:**

- **S6 is scored fully but optimised only partially.** `analysis/criteria.py` scores every room
  correctly after the fact; `solver/objective.py` can only post a term for non-cumulative room types
  (Salle). Closing it needs `solver/variables.py` changes.
- **Regeneration is half-built.** The catalogue and the translation of all three actions exist;
  turning an accepted recommendation into a new run does not. ⚠️ **And `recommendations/` has no tests
  at all** — no test in the repository imports it.

~~**H10 is registered but dormant**: `build_variables` refuses to run if any session is locked.~~
✅ **Closed 2026-08-06, Phase 7 M1 (C-19)** — `SolverInput` carries `frozenset[Placement]`, H10 prunes
domains like the other five domain-pruned rules, and `tests/integration/test_h10_locks.py` verifies it
against the real solver. It was FR-23's prerequisite.

Persistence of runs and candidates was never Phase 3 work — it is Phase 5's run record.

📄 **Full module-by-module account, the ITC-2007 figures and the authority table:
[`docs/history.md`](history.md).**

### Phase 4 — Web interface · ✅ **complete 2026-08-01** · 4 days

**Purpose.** The complete path from a teacher declaring availability to a published timetable.

**Delivered.** Six milestones: the API foundation, the run lifecycle and executor, and four screens —
availability, generation, timetables, comparison. First frontend tests. **C-12(a)** resolved (two-state
grid) and **C-14** deferred, both recorded before the code was written.

**Its closing audit found 17 defects, plus one the audit itself introduced and caught on the next
pass** — which is why a clean pass has to be a *whole* pass. Not one was caught by `run-checks.ps1`.

⚠️ **One thing it owed and could not close:** the FR-2 acceptance criterion, *"filled in under 5
minutes without training"*. It is about a person. **Still unmet** — protocol in
[`docs/demonstration.md`](demonstration.md) §2.

📄 **Full milestone-by-milestone account and the audit's defect table: [`docs/history.md`](history.md).**

### Phase 5 — Pre-analysis in-app, diagnosis, auth, run record · ✅ **complete 2026-08-04** · 2 days

**Purpose.** An infeasible instance must produce a report naming the rules in conflict, not a timeout;
every published timetable must trace back to its run, seed and weights.

**Delivered.** Six milestones: FR-12's five checks in-app with **both** bounds, FR-8's diagnosis run,
FR-19's run record in PostgreSQL, FR-11's authentication and rights, publication with its trace, and
the closing audit. **C-17** and **C-18** resolved, both recorded before the code.

**The two findings worth carrying forward:**

- **C-17** — the documented diagnosis mechanism (enforcement literals as assumptions) was built,
  tested, and then measured **unusable at reference scale**: a literal takes its constraint out of
  presolve, so an infeasibility a plain solve proves in **0.0 s** returned `UNKNOWN` after 240 s. Stage
  3 now withdraws one rule at a time and solves plainly — **`('H3',)`, minimal, in 1.9 s**.
- **A tenth import contract, `api ⇸ db`**, verified to fire before being relied on. And the
  store-contract suite found a real divergence on its first run: the *in-memory* store violated
  invariant 6 while the SQL store refused.

📄 **Full milestone-by-milestone account and the audit's eight defects: [`docs/history.md`](history.md).**

### Phase 6 — Tests, documentation, presentation · ✅ **complete 2026-08-06** · 3 days

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
| **M4** | **FR-9 acceptance test** — a half-day closed in configuration, no source file touched | ✅ **done 2026-08-05** — **criterion 7 met**, and the closure lands at exactly 100.0 % of Lab_Info's windows |
| **M5** | **Instance generator** (`data/generator/`) | ✅ **done 2026-08-05** — passes `verify_instance.py` on its own output, and the result solves |
| **M6** | **Demonstration script + the FR-2 walkthrough protocol** | ✅ **done 2026-08-06** — `docs/demonstration.md`; found and fixed a defect that made the seed command useless |
| **M7** | **Documentation, traceability, closing audit** | ✅ **done 2026-08-06**, five defects found — one of them in the `README`, which no previous audit had checked |

**Scope decisions taken by the project owner on 2026-08-05, before any code:**

1. **The assistant and regeneration are deferred, and the deferral is written down.** FR-22, FR-23,
   FR-24 and FR-25 stay `—`; `assistant/` stays scaffold-only. ADR-010 commits them to increment 1 and
   PPM Table 8 budgets them into no phase — that is C-1, and Phase 6 is not where it is absorbed
   silently. `testing-strategy.md` §4's four assistant rows are marked out of scope with the reason.
   FR-23 additionally needs H10's dormant gap filled (item 9 of `status.md`'s "Next, in order").
   ⚠️ *That prerequisite was filled on 2026-08-06 by Phase 7 M1; the sentence above records Phase 6's
   scope decision as it stood and is kept for that reason.*
2. **The generator reproduces every documented figure, and `data/instance/` is not touched.**
   Byte-exact reproduction is **not achievable** — 425 student names and 218 teacher assignments came
   from a random stream that was never committed, so a "generator" emitting them exactly would be a
   copy wearing a generator's name. ADR-008 and C-11 record what is and is not achieved.
3. **The presentation deliverable is a reproducible demonstration script** in `docs/`, each step
   stating its expected result so a failed demonstration is visible rather than improvised around.
   ✅ Delivered in M6 as [`docs/demonstration.md`](demonstration.md).

**Also lands here.** The **instance generator** (`data/generator/`), a stated PPM §10 deliverable that
does not exist — item 10 of `docs/status.md`'s "Next, in order". It must reproduce *the* documented
instance, not merely a valid one (ADR-008). And the **timed FR-2 walkthrough**: the availability grid
is built, but "filled in under 5 minutes without training" is about a person and no automated check
stands in for it.

**Status. COMPLETE 2026-08-06 — all eight milestones and a closing audit.** **Eight of nine** acceptance criteria are met; the ninth needs a person. ⚠️ **Increment 1 is not complete with it** — see the header of this file.

#### The closing audit, 2026-08-06

**Five defects, and not one was caught by `run-checks.ps1`** — green before the audit, green after
every fix, green throughout. Third phase running. Same method as Phases 4 and 5: **compare documents
against the repository, never against other documents.** Every defect below was found by checking a
claim against a `grep`, a file count, a dependency manifest, or the running code.

| Kind | Found |
|---|---|
| ⚠️ **A document no previous audit had opened** | **`README.md`'s Status section was two phases stale**: *"Phases 1–4 complete, Phase 5 in progress (4 of 6 milestones)"* and *"Publication and the closing audit remain"*, both false since 2026-08-04. It is the repository's front door and the first file any reader opens. **Phase 4's audit and Phase 5's both checked `dashboard.md` and `status.md`; neither checked `README.md`** — the method was right and its *scope* was too narrow |
| **A capability claimed that does not exist** | **Four documents claimed CI enforcement.** `README.md` said the layer separation *"is enforced in CI by `import-linter`, so a violation fails the build rather than a review"*; ADR-004, `data-and-instance.md` and `CLAUDE.md` said the same in their own words. **There is no CI configuration in this repository** — `.github/` does not exist and no other pipeline file does. The ten contracts are real and do fire; nothing runs them automatically |
| **A test claimed that does not exist** | This block said the recommendation catalogue and translation *"exist and are tested"*. **No test imports `optiedt.recommendations`** — `translator.py` and `catalogue.py` have **zero coverage**. The claim survived because `recommend()` in `analysis/ranking.py` *is* tested and carries a similar name |
| **A row describing the past as the present** | The API·frontend row read *"Four screens … over ten endpoints"* — Phase 4's figures, still stated as current. There are **seven screens** and **15 endpoints** |
| ⚠️ **A defect that made a command useless** | Found in **M6**, by writing the demonstration script rather than by auditing: `services/seed.py` derived the password **twice**, printing one and storing another whenever `OPTIEDT_SEED_PASSWORD` was unset. Every account was created with a credential nobody was shown. **Every test pinned the environment variable**, so both calls agreed and the divergence was invisible; `main()` is `# pragma: no cover` |

**What the audit did not find:** any architecture violation (10/10 contracts kept throughout), any
`TODO` in source, any broken module path — **all 157 file paths quoted across the documentation exist**
— any error in `open-questions.md`'s bookkeeping (seventeen codes, C-1 to C-18 with no C-10, two open
and fifteen resolved, consistent), and no acceptance criterion marked wrongly (nine listed, eight
ticked, one unticked and correctly so).

⚠️ **The lesson this audit adds to the previous two.** Phases 4 and 5 established *compare against the
repository*. This one shows that is necessary and not sufficient: **the method must also name which
documents are in scope.** Two audits ran a correct method twice and missed the front door, because
nothing said the front door was part of it. A checklist that omits a file cannot notice the file. Before it, six: Phase 5 added **two**, a teacher's own data
(M4) and a published timetable's trace (M5). M2 ticked none; it turned the six from *measured once by
hand* into *checked by the suite*, which is what Phase 6 owes them. **M3 measured criterion 5 and it
was decided on the measurement** — see below.

**The one that remains** is the timed FR-2 walkthrough, which needs a person and is M6's.

✅ **Criterion 5 was decided on 2026-08-05 and REWORDED rather than merely ticked.** Measured on both
shapes it holds on one and not the other, so a tick against the original wording would have claimed
something the product does not do. It now reads: *"an instance without a solution produces a report
naming the rules in conflict where CP-SAT can prove the infeasibility, and a pre-analysis report naming
the resource and the quantity missing where it cannot."* What is satisfied on **both** shapes is the
phase's stated purpose — **a report rather than a timeout** — and the limit is measured, tested and
documented rather than hidden. Same treatment as C-5: the wording moved, the implementation did not.

#### M3 — what landed, 2026-08-05, and the question it settles

`tests/acceptance/test_fr08.py` and `test_fr12.py`, **17 tests**, both infeasible shapes exercised end
to end through the API. Measured rather than assumed:

| Shape | Pre-analysis | Stage 2 | Stage 3 |
|---|---|---|---|
| **Area** — 4 of 8 computer laboratories, 160 periods against 112 | fails, names `Lab_Info` **short by 48 periods / 36 windows** | `INFEASIBLE` | **`DIAGNOSED`, `('H3',)`, minimal, conclusive** |
| **Contiguity** — the pre-C-13 mix | fails, names `Lab_Info` **short by 14 windows**, `Lab_Sciences` by 2 | `UNKNOWN` → raises → **`FAILED`** | never reached |

⚠️ **So criterion 5 - "an instance without a solution produces a report naming the rules in conflict" -
is met on infeasibilities CP-SAT can prove, and not met in general as originally worded.** On the contiguity shape the user
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

#### M4 - what landed, 2026-08-05, and it ticks criterion 7

`tests/acceptance/test_fr09.py`, five tests. Wednesday afternoon closed by setting `Slot.is_open =
False` and **nothing else**; the run launched through the API against the production solver; no
placement in any of the three candidates occupies a closed slot - **occupancy** checked rather than the
start index, since a two-period session could straddle one. All 218 sessions still placed.

**"With no code change" is asserted rather than described.** The catalogue still holds exactly H1-H12,
and the two instances differ in `Slot.is_open` **alone** - sessions, rooms, teachers, availability and
constraints identical, every slot INDEX unchanged, which is what lets a shortened-day window shift
displayed hours without moving a variable (ADR-003). A test that closed the half-day by calling some
helper inside the solver would have passed while proving the opposite of the criterion.

⚠️ **Not a formality on this instance, and the figure is worth carrying.** Any half-day closure costs
each room one two-period window, and `Lab_Info` has exactly **8 spare across 8 rooms** - so the
closure takes it to **exactly 100.0 % of its two-period windows**. A solution exists only if a perfect
packing does. Measured on three different half-days: it does, in 13-49 s to feasibility. The
pre-analysis reports the new figure, so an operator can see that the *next* closure has nowhere to come
from.

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