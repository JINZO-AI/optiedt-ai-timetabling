# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

> 📍 **For "what phase are we in?" read [`docs/project-roadmap.md`](project-roadmap.md).** It maps the
> whole project — the plan's phases, increment 1 and increment 2 alike — onto **one continuous numbered
> sequence**, which is the project owner's tracking view. **Currently Phase 9 of 14.** This page stays the
> handoff page and the traceability table stays the authority on any single requirement.

**Last updated 2026-08-07. Phase 7 is COMPLETE — all seven milestones and a closing audit.**

> ### Is this page still true? Check before trusting it
>
> This is the **only** place the project's current state is recorded, so a stale line here misleads
> every session that follows. Three commands settle it in under a minute:
>
> ```
> git log -1 --date=short --format='%ad %s'     # newer than the date above?
> git log --oneline <that date>..HEAD           # what landed since
> scripts/run-checks.ps1                        # is the repository actually green
> ```
>
> **If the last commit is newer than this page's date, believe the commits and repair this page first.**
> That is not a formality: the "Overall progress" row below described a phase that had already finished
> and **survived two closing audits**, and `README.md`'s Status section went stale in two successive
> phases — once *because the audit that fixed it ran before the phase it was recording had closed.*
>
> ⚠️ **A closing audit cannot verify the sentence announcing its own phase closing.** Whoever closes a
> phase writes that line *after* the audit, and nothing checks it. It is the single most likely line on
> this page to be wrong.

✅ **INCREMENT 1 IS COMPLETE.** Phase 7 was approved by the project owner on 2026-08-06 and delivered
the four requirements that had no home: **FR-23** (regeneration) and **FR-22, FR-24, FR-25** (the
assistant). **C-1 is closed** — recorded 2026-07-29, scheduled 2026-08-06, delivered the same day.

**What that means in the product.** An accepted recommendation now changes one solver input and
launches a **new run** through the same engine; H10 executes, so all twelve hard rules run; and the
language service explains, answers and reports from figures the analysis layer computed, with every
number it writes checked against the context it was given.

✅ **FR-24 reached `✓` on 2026-08-07**, and *how* matters more than the tick. It was held at `WIP`
because **no test establishes that a real provider answers a question well, and none can** — a model's
output is not fixed by a seed (**C-21**). That gap was never closable by a test, so it was closed the
way the documentation always said it would be: **one deliberate live call, performed and recorded in
[`docs/demonstration.md`](demonstration.md) §4** (Groq · `llama-3.3-70b-versatile`, 3 of 3 answers
generated, none discarded, figures matching the screen).

⚠️ **The suite did not change and must not be read as having changed.** **No test calls a live
provider**, before or after. Read a green suite as *the application behaves correctly around a language
model*, never as *the assistant was tested against one*. The `✓` rests on a dated record of one call,
not on automation — and §4 records an imprecision inside that very answer, because the grounding check
verifies figures and never the sentence around them.

⚠️ **Performing it found a defect that no amount of reading had.** `assistant/adapter.py` sent no
`User-Agent`, so `urllib`'s default was refused by the provider's CDN (HTTP 403 / Cloudflare 1010) and
every answer fell back to its computed form — **degraded mode working exactly as specified, which is
why nothing failed loudly and why four audits saw nothing.** Fixed 2026-08-07 and pinned by a test that
intercepts `urlopen` and calls no provider.

⚠️ **A figure the project carried for eight days was wrong, and Phase 7 is where it surfaced.** C-1's
~2.5 unbudgeted days is itemised in ADR-010 as *adapter + context builder + verifier ≈ 1.5 d, panel
≈ 0.5, report ≈ 0.5* — every line of that is assistant work, and **regeneration appears in none of
it**. The overrun was understated because a figure was repeated rather than re-derived. Recorded
rather than quietly corrected; ADR-010 is unchanged, as instructed.

✅ **All nine acceptance criteria are now met**, the ninth on 2026-08-07. ⚠️ **The ninth was REWORDED
rather than met as written**, by project-owner decision and for the third time in this project (after
C-5 and criterion 5): it read *"filled in under 5 minutes without training"* and **the run did not
measure the time**, so the wording dropped the clause the evidence could not support. The participant
was the **project owner**, who had not seen the screen but does know the domain, and no naive
participant was available. **Read `docs/demonstration.md` §2 before quoting the tick** — the same
session reported the navigation confusing, which is a usability finding rather than FR-2 evidence.
Phase 7 added no acceptance criterion and moved none: its four requirements are verified against
`docs/testing-strategy.md` §4's rows, which are a different list.

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **Increment 1 is COMPLETE.** All seven phases delivered — the plan's six (20 days) plus Phase 7, approved 2026-08-06 for the work C-1 recorded and no phase carried. By *delivered product*: **8 of 9 acceptance criteria** met (the ninth on 2026-08-07, ⚠️ **reworded** — no time was measured), and **10 of 25 requirements `✓`, 11 under way, 4 not started** (2026-08-07 promoted three: FR-24 on the live call in `demonstration.md` §4, FR-2 once its walkthrough was settled and `acceptance/test_fr02` was written, and FR-13 once **C-15** was resolved on measurement) — a requirement is `✓` only once a user can reach it *and* it is tested end to end. ⚠️ **This row said "75 %, Phases 1–4 delivered, Phase 5 under way, 0 requirements finished" until 2026-08-06** — false since 2026-08-04 and 2026-08-06 respectively, and missed by two closing audits. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 7 — the assistant and regeneration. COMPLETE 2026-08-06**, all seven milestones and a closing audit. Milestone table in the Phase 7 block below |
| **Last completed phase** | **Phase 6 — COMPLETE 2026-08-06**, eight milestones and a closing audit: the acceptance suite, the instance generator, the demonstration script, C-5 and C-14 implemented. Before it, Phase 5 delivered pre-analysis in-app, the diagnosis run, the run record, authentication and publication |
| **Milestone reached** | **Phase 7's, 2026-08-06** — *increment 1 closed*: FR-23 regenerates through the same solver, and the assistant explains, answers and reports under a grounding check. **C-1 is closed after 8 days open** |
| **Current goal** | ⚠️ **None — increment 1 is delivered and no phase is open.** Increment 2 is *conditional on remaining time* and its content is fixed: the examination session (4 d) and weight adjustment from recorded comparisons (3 d). Natural-language constraint entry is **not undertaken** (`docs/ai-integration.md`) |
| **Next task** | ⚠️ **A decision, not code, and it belongs to the project owner.** Two things are outstanding and neither is a defect: **(1)** ~~the timed FR-2 walkthrough~~ — **run and settled 2026-08-07, criterion reworded** (`docs/demonstration.md` §2); and **FR-2 is `✓`**, its `acceptance/test_fr02` written the same day); **(2)** whether to open increment 2. ~~*(3) a first live provider call*~~ — **performed 2026-08-07**, recorded in `demonstration.md` §4, and FR-24 is `✓`. **C-9 remains open** and blocks three requirement ticks (FR-6, FR-10, FR-18); **C-15 was resolved 2026-08-07** and FR-13 is `✓`. See the Phase 7 block for the full list |
| **Branch** | `main`. ⚠️ **Whether it is ahead of `origin/main` is NOT recorded here**, deliberately — and this row said *"ahead of `origin/main` by unpushed local commits"* until 2026-08-07, when everything had in fact been pushed. It is the same fault as the SHA in the row below and it has the same cause: **a push that does not touch this file cannot correct a claim stored in it.** Derive it — `git fetch`, then `git rev-list --count origin/main..HEAD` (0 means everything is pushed) |
| **Latest commit** | **Not recorded here** — it is stale the moment anything is committed. `git log -1 --oneline`. The durable fact is the last *pushed* commit, in the row below |
| **Repository status** | **No SHA and no commit count are recorded here. Derive them:** `git log -1 --oneline` · `git rev-parse --short HEAD` · `git rev-parse --short origin/main` · `git rev-list --count origin/main..HEAD` (0 means everything is pushed). Run `git fetch` first, or `origin/main` is only as fresh as your last one. ⚠️ **This row recorded a SHA and was wrong five times** — the fifth found on 2026-08-04, when it still named the Phase 4 audit commit and `origin/main` had moved two commits past it. Four of those five were *repaired by editing the value*, which is why there was a fifth: **a SHA cannot survive a push that does not touch this file, and a count cannot live in a file that commits change.** The values are therefore gone rather than corrected. The full record of each failure is in [`docs/history.md`](history.md) |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green across **nine** steps: **510 backend tests + 53 frontend**, **11/11 layer contracts** kept, mypy strict on **78** files, instance verified, **38 store-contract tests against real PostgreSQL** and **2 migration tests**. Separately, `scripts/run-acceptance.ps1` green: **106 acceptance tests over 14 requirements** (FR-3, 5, 8, 9, 11, 12, 13, 15, 17, 19, 22, 23, 24, 25), of which **35 solve for real**. **9 of 9 acceptance criteria met**; ⚠️ the ninth **reworded** 2026-08-07, no time measured. The engine is validated on all 21 published ITC-2007 instances, and the whole path — declare availability, generate, compare, regenerate, explain, publish — is verified against the real solver |

```
Increment 1   ████████████████████  COMPLETE - 20 budgeted days + Phase 7's unbudgeted work

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ████████████████████  ✅ done
Phase 4  Web interface — grid, generation, comparison  ████████████████████  ✅ 6/6 milestones
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ████████████████████  ✅ 6/6 milestones
Phase 6  Tests, documentation, presentation            ████████████████████  ✅ 8/8 milestones
Phase 7  Regeneration and the assistant  (unbudgeted)  ████████████████████  ✅ 7/7 milestones
```

*The plan budgeted 20 days over six phases (3 + 5 + 3 + 4 + 2 + 3). **Phase 7 was budgeted none** —
that is C-1, and it is why the increment closed past its plan rather than inside it.*

✅ **The contradiction this block recorded is resolved, and the resolution is the seventh bar.** It
read: *"The heading of `docs/status.md`'s phase table reads `Phases — increment 1, 20 working days`,
which equates the six phases with the increment; ADR-010 commits FR-22, FR-23 and FR-24 to increment 1
and the six phases name none of them. Both statements are in this repository and they cannot both be
right."*

**They could not, and the phase table was the one that moved.** ADR-010 is a delivered commitment and
was not touched; the plan's six phases were never the whole of increment 1, and Phase 7 is what makes
the two statements consistent. `docs/status.md`'s table now carries Phase 7 with its days marked
**unbudgeted**, which is the honest form: the work was always committed, and it was never costed.

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **11/11 contracts kept**. The eleventh (Phase 7 M2) keeps `recommendations` off the solver, which is what stops FR-23's "new run through the same engine" from becoming a private solve with no run id, no seed and no trace; verified to fire by injecting a violation before being relied on. The tenth (Phase 5 M3) keeps `api` off `db`, so the router layer never learns how anything is stored; verified to fire before being relied on, like the eighth and ninth. No layer edge has been weakened; the count has only ever gone up. The eighth (2026-07-31) keeps the ITC-2007 harness out of the product; the ninth (Phase 4 M1) keeps `api` off the solver. Both were verified to fire before being relied on |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 fully closed — accounting (`x[s,t₀]`, `y[s,t]`) built on demand, auxiliaries measured at **5,249**. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions; `engine.py` posts it — and builds occupancy at all — only when a criterion carries weight, so an all-zero profile is genuinely equivalent to a feasibility solve. **Deterministic budget calibrated 2026-07-30** — it binds exactly, per worker; 1 unit ≈ 4.8 s wall at one worker, ≈ 19 s at all sixteen. **`interleave_search = true` is set and is required for reproducibility** (C-16, ADR-011 amended); the warm start is withheld when an objective is posted, because it pinned all three profiles to one timetable |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance/**recommend** — FR-16). **The four properties the specification requires** (`docs/scoring-and-explanation.md`) all pass, verified by **ten** hypothesis tests in `tests/property/test_scoring_properties.py` — four specified, ten tests; the extra six cover edge cases the four imply but do not state |
| **Portfolio** | 🟢 `services/portfolio.py` — the only module importing both `solver` and `analysis`, which is what `services` is for. Defines the three profiles, divides the total budget between them, solves sequentially under one fixed seed, removes duplicate timetables and ranks the survivors under one weight vector. 16 unit tests pin the rules against a recording fake solver. Measured on the reference instance: **3 distinct candidates in 147–150 s**, reproducibly, total budget 90 (C-16) |
| **Persistence** | 🟢 **Built, Phase 5 M3 (FR-19).** PostgreSQL 17 behind the Protocols Phase 4 left in place — **no router changed**, which is what those Protocols were for. `db/models.py` normalises what `docs/domain-model.md` calls an entity (run, weights, candidate, placement, sub-score, check) and keeps two short ordered lists as JSON. Alembic was configured but never initialised; `migrations/env.py` now reads the URL from `Settings` so one connection string governs both the API and the migrations. **Verified by killing the API and reading a run back from a fresh process.** ⚠️ `persistence` is configuration, never detection: a store that fell back to memory when the database was unreachable would lose every run while looking healthy, which is the opposite of FR-19 |
| **API · frontend** | 🟢 **Complete for Phase 4, extended since.** ⚠️ *This row said `Four screens … over ten endpoints` and was describing Phase 4's close as if it were the present; corrected at Phase 6's audit to seven and 15, and corrected again at Phase 7's to **eight screens** — availability, generation, timetables, comparison, sign-in, conflict report, publications, and the assistant panel — over **19 endpoints**. **Derive both rather than editing them**, which is the whole lesson of a figure that has now gone stale twice: `Get-ChildItem frontend/src/features -Directory` (`admin/` is a placeholder and is not a screen) and `Select-String backend/src/optiedt/api/routers/*.py -Pattern '^@router\.'`.* React shell with `react-router` and `@tanstack/react-query`; `features/generation` launches a run, polls it and renders the ranked candidates with all seven sub-scores; `features/timetable` shows a candidate by teacher, group, room and as room occupancy (FR-7, FR-18). **A group's view includes its ancestors' sessions** — a CM gathers the whole promotion, so a subgroup shown only its own sessions would display a week with holes its students do not have. ⚠️ **The frontend computes no score and decides no ranking**: rank order is the array order the API returns, and every figure shown arrives already computed (`docs/architecture.md`: the presentation layer may not "compute a score, decide an order"). It *does* arrange for display — grid axes, rooms alphabetically, and largest-remainder rounding so a contributions column adds up — which is what "display, filter, print" permits. Do not restate this as "the frontend computes nothing"; that is falsifiable by one grep and invites someone to conclude the rule is not meant seriously. The endpoints are `/api`, which `vite.config.ts` already proxies: the instance, FR-2's availability read/write, `POST /runs` → **202** with polling on `GET /runs/{id}`, and the candidate, comparison, dominance and recommendation reads. `tasks/executor.py` runs solves in-process on a **single-worker pool** (ADR-005) — one solve at a time, because each already uses every core. Both stores were **in memory** at Phase 4's close, behind Protocols; **Phase 5 M3 substituted database-backed ones and no router changed**, which is what those Protocols were for. A ninth import contract, `api ⇸ solver`, was added here and verified to fire; M3 added a tenth, `api ⇸ db` |
| **Pre-analysis** | 🟢 **Built, Phase 5 M1.** `preanalysis/verifications.py` — the five checks, **both** the period bound and the contiguity bound, run in every run's `PREANALYSIS` state against the instance about to be solved. Compared numerically against `data/verification/verify_instance.py` rather than trusted to agree with it. The C-13 regression is pinned by a test that reconstructs the pre-repair room mix. It imports `domain` and nothing else — the `preanalysis ⇸ solver` contract is what keeps it the instrument that tells an infeasible instance from a modelling regression |
| **Assistant** | 🟢 **Built, Phase 7 M3 (FR-22).** Adapter, context builder, answer verifier, computed forms and three routes — `assistant/` is no longer scaffold. ⚠️ **Off by default**, so **degraded mode is the ordinary configuration**: every other test in the suite runs against an application with no language service, which is invariant 5 exercised continuously rather than once. The grounding check is `numbers(answer) ⊆ numbers(context)`; an ungrounded answer is **discarded whole**, not repaired, and the computed form is shown with `generated: false` and a reason. ⚠️ **The scaffold's `ContextBuilder.build(kind, run_id)` could not be implemented without a store** — looking a run up is the database — so the signature takes `RunFacts` and the router assembles it. **C-21: no test calls a live provider**, and a green suite therefore says the application behaves correctly *around* a model, never that a model was tested. ⚠️ **That is unchanged by the first live call of 2026-08-07** (`demonstration.md` §4) — which is exactly the point: the call is a dated record, not a test, and it is what FR-24's `✓` rests on. It also found the one defect four audits missed, a missing `User-Agent` that a CDN refused |
| **Validation** | 🟢 `scripts/run-checks.ps1` green, **nine steps**: layer boundaries (**11/11 contracts**) · ruff · format · mypy strict on 78 files · **404 fast backend tests** (including the 71 acceptance tests that need no solver) · **database tests against real PostgreSQL** · instance verification · frontend `tsc` · frontend tests. ⚠️ The database step **fails when no database was reached** — a forgotten `docker compose up -d`, which is actionable — and **skips** when Docker is absent, saying plainly that FR-19's persistence was not covered. ⚠️ **That failing half did not work until Phase 6 M1**: it checked the Docker *daemon*, so a stopped container let all 38 tests skip under a green tick. It now checks that tests actually **passed**, and the guard was verified to fire. `pytest` exit 5 is **no longer tolerated** (Phase 4 M1) — with 287 tests collected, allowing "collected nothing" would let a broken import pass as success. Separately, `scripts/validate-itc2007.ps1` runs the engine against the 21 published ITC-2007 instances — not in `run-checks` because a full sweep takes tens of minutes — and **`scripts/run-acceptance.ps1`** runs the **106** acceptance tests in **16–22 min** (measured 16 min 23 s idle on 2026-08-06, 21 min 38 s under concurrent load on 2026-08-07 — ⚠️ a range, because ADR-011's "wall-clock cost varies by machine" applies here too), of which **35** solve for real — four production portfolios: one shared by FR-3/FR-13/FR-19, a second for FR-19's repeat, and two for FR-23's origin-and-regeneration pair |
| **Tests** | 🟢 **510 backend** (404 fast + 62 solver-marked + **44 database-marked**) **+ 53 frontend**. **Phase 7 M5 added 10** — `acceptance/test_fr25.py`, including that the report **says plainly when nothing was published** (silence would read as an omission rather than an absence) and that the published candidate is **looked up by the router and passed in as a value**, because the assistant may not fetch it. **Phase 7 M4 added 9 backend and 10 frontend** — `acceptance/test_fr24.py` (both ways the criterion can be met: a model that declines, and a model that does not and is stopped; plus the check that no personal field reaches the payload) and `features/assistant/Answer.test.tsx` (that generated and computed text are never presented alike, that the computed form reads as an answer rather than a failure, and that a discarded answer's reason is surfaced). **Phase 7 M3 added 39** — `unit/test_assistant.py` (30) and `acceptance/test_fr22.py` (9, all solver-free because the criterion is about the service being OFF). ⚠️ **One of them found a real hole in the grounding check on its first run**: the number pattern was `\d{1,3}(?:[ ]\d{3})*`, so **`4271` matched nothing at all** and passed as grounded — as would any ungrouped number above 999, which is exactly the range an invented count of minutes or periods falls in. Pinned by a parametrised regression. **Phase 7 M2 added 49 backend and 11 frontend** — `acceptance/test_fr23.py` (14: ten about the application through the API, four solver-marked at production settings including **the regenerated candidate re-derived against H1, H3, H8, H9**), `unit/test_regeneration.py` (21: the three assembly rules and every refusal), **`unit/test_recommendations.py` (8 — the FIRST tests `optiedt.recommendations` has ever had**, which the Phase 6 audit found had zero coverage while a document claimed otherwise), `integration/test_migrations.py` (2 — the migrations must produce the schema the models declare; verified to fire by adding a model column with no migration), 2 store-contract tests over both stores, and `RegenerationPanel.test.tsx` (11 — that the screen never reads as an edit). **Phase 7 M1 added 13** — 9 in `tests/unit/test_solver_variables.py` (H10 narrows the start domain and the candidate rooms, touches no other session, and **cannot grant** a slot or room a hard rule forbids) and `tests/integration/test_h10_locks.py` (4 solver-marked: a lock survives a real solve, ten locks across room types survive together, and the limiting case — **all 218 placements locked returns exactly the timetable given**). It replaced `test_locked_sessions_not_yet_supported`, which pinned the dormant behaviour. **Phase 6 M5 added 26** — `tests/unit/test_generator.py`, which runs the generator as a subprocess and holds its output to `verify_instance.py`, the same contract the committed files are held to. **M4 added 5** — 	est_fr09, which ticks acceptance criterion 7. **M3 added 17** — 	est_fr08 (both infeasible shapes, end to end) and 	est_fr12 (the resource and the quantity named, including the C-13 contiguity bound). **Phase 6 M2 added 42** — the acceptance suite, `tests/acceptance/`, one file per requirement and each opening with the criterion it verifies: `test_fr03` (H1–H12 re-derived from the placements a user obtains through the API), `test_fr05`, `test_fr11` (real tokens, no dependency override), `test_fr13` (three distinct candidates, C-5's wording), `test_fr15`, `test_fr17` (C-14's reworded dominance), `test_fr19` (reproducibility *and* the publication trace — one requirement, two criteria). **Phase 6 M1 added 3 backend and 8 frontend** — the Pareto rule's new edge cases (`test_two_candidates_equal_on_every_criterion_dominate_neither`, and at catalogue weights the case C-14 turned on: beaten on all six weighted criteria, tied on S10) and `DominanceNotice.test.tsx`, which pins that an empty result reads as "checked, none found" rather than as a screen that does nothing. **M5 added 8 backend and 5 frontend** (`tests/integration/test_publication.py` — the trace checked against the RUN, not against a second copy of the seed; `TraceTable.test.tsx` — the whole weight vector on screen). **M4 added 25** (`test_rbac.py` against REAL tokens, `test_seed.py`). **M3 added 34** (`tests/integration/test_store_contract.py` — ONE suite run twice, over the in-memory store and over real PostgreSQL). **M2 added 13 backend** (`tests/unit/test_diagnosis.py` — the conflict set named exactly, against real CP-SAT, plus the guard that an enforcement literal genuinely relaxes its constraint) **and 6 frontend** (`ConflictReport.test.tsx` — the report never claims minimality, never reads as a repair list, and never shows an empty set as reassurance). **M1 added 32 backend and 5 frontend**: `tests/unit/test_preanalysis.py` (the five checks against hand-computable instances, and **the C-13 regression** — the pre-repair room mix must be caught by the contiguity bound), `tests/integration/test_preanalysis_matches_verifier.py` (the in-application checks against the standalone verifier, every figure re-derived from the raw CSVs) and `frontend/src/features/generation/PreAnalysisReport.test.tsx` (the figures reach the DOM; an empty report reads as "not run"). The frontend tests began in Phase 4 M5 (`vitest` + `@testing-library/react`) and `run-checks.ps1` runs them: they assert on **rendered** figures, which `tsc` cannot, and the acceptance criterion is about what is *displayed*. They caught a real rounding defect on their first run. Phase 4 also added `tests/unit/test_api_schemas.py` (the wire format: French enum literals, camelCase fields — the guard against the `RoomType` defect returning), `tests/unit/test_availability_api.py` (FR-2's replace-wholesale rule and the `SYNTHETIC`/`TEACHER` distinction), `tests/unit/test_run_lifecycle.py` (the state machine, including that `DIAGNOSING` is reachable only from `INFEASIBLE`) and `tests/integration/test_api_runs.py` (the run endpoints against a **fake solver**, so they stay in the fast suite and carry no timing assumption — the test waits on the executor's Future). Phase 3's 125 are unchanged. New in Phase 3: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended), `tests/unit/test_itc2007_cost.py` and `tests/integration/test_itc2007_validation.py` (ITC-2007's rules against hand-computed values, and against seven solutions the archive publishes) |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification. ⚠️ **It does not block the Phase 6 acceptance suite** — neither the nine criteria nor `testing-strategy.md` §4's table names any of the four. Corrected 2026-08-05 | The `✓` of FR-6, FR-10, FR-18 | Technical lead |
| ~~**C-15**~~ | ~~The objective weights raw violation counts of incomparable scale~~ — **RESOLVED 2026-08-07 on measurement, by refuting its own diagnosis.** The objective formulation is sound and unchanged; `teacher-favouring` now raises **S3 and S4** rather than S3 and S5, S5 being an admitted proxy (C-12) and the costliest criterion to optimise. Measured: S3 **29 → 0**, S5 103 → 95, score 79.45 → 81.10 | ~~FR-13~~ — **unblocked, FR-13 is `✓`** | ~~Technical lead~~ |

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
| ~~**~2.5 unbudgeted assistant days**~~ | ~~≈12 % overrun on 20 days~~ | **REALISED and CLOSED 2026-08-06 by Phase 7.** The release valve was never used — the report shipped. ⚠️ **The figure was understated**: it costed the assistant and not FR-23 (see `docs/status.md`) |
| ⚠️ **No test can establish that a real provider works** (C-21) | **Still true and permanent** — it is why FR-24's `✓` rests on a dated record rather than on the suite | Deliberate. A model's output is not fixed by a seed. **The first live call was performed 2026-08-07** and is recorded in [`docs/demonstration.md`](demonstration.md) §4; the suite remains provider-free. ⚠️ **A green build is still not evidence about a model**, and one recorded call is not evidence about every call |
| **91 % laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and an infeasible instance looks like a slow model** | Pre-analysis first, always. Read the *window* figure, not the period figure |
| **A check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is blamed on the model. Cost three sessions on C-13 | Both bounds now checked. **FR-12's port must carry both** |
| ⚠️ **`interleave_search` is marked "Experimental" upstream** | Reproducibility — a written acceptance criterion — now rests on one OR-Tools parameter whose guarantee could change between releases. **And it already has one measured side effect**: `CpSolver.objective_value` can be reported 5–15 units above the objective at the solution actually returned, on solves that stop before proving optimality (found 2026-07-31 on ITC-2007 comp02/18/21) | **Pin the OR-Tools version.** `tests/integration/test_reproducibility.py` verifies reproducibility at production settings rather than trusting the docs; a failure there is blocking, not flaky. The objective-reporting quirk **affects nothing**, because no score, ranking or display reads `SolverOutput.cost` — the analysis layer recomputes from the placements, which is what the ban on `analysis → solver` forces. **Do not start ranking on `cost`.** Full account in ADR-011 |
| ~~**Deterministic-time calibration**~~ | ~~"the budget does not bind, ~11× over-run"~~ | **RESOLVED 2026-07-30 — the claim was false.** The budget binds *exactly*, per worker; `deterministic_time` reports the sum across workers and ~11 was the worker count on a 16-core machine. Calibrated figures in `docs/status.md`; correction in C-2 |
| ~~**Raw-weight objective lets a large-scale criterion swamp a small one**~~ | ~~teacher-favouring is effectively S5-only~~ | **RESOLVED 2026-08-07 (C-15), and this row's diagnosis was wrong.** The raw-weight formulation is sound and **unchanged**. Both fixes this row proposed were measured and refuted — normalising by bound range is **worse** (S3's range is the largest of the seven: raw S3:S5 = 1:1.33 → 1:4.6). The fault was *which criteria the profile raised*: S5 is an admitted proxy (C-12) and the costliest criterion to optimise. `teacher-favouring` now raises **S3 and S4**; S3 **29 → 0** (the proven single-criterion optimum), S5 103 → 95, score 79.45 → 81.10 |
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
  0 duplicates removed, in 147–150 s**, each scored /100 with its seven sub-scores. ✅ **The profiles now steer as their names promise, since 2026-08-07.** This bullet read "teacher-favouring improves S5 and not S3, for the documented reason (C-15, deferred)". C-15 was resolved by measurement: the objective formulation was never the fault, and `teacher-favouring` now raises **S3 and S4** rather than S3 and S5. Measured S3 **29 → 0**.
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
- ~~**Regeneration is half-built.** The catalogue and the translation of all three actions exist;
  turning an accepted recommendation into a new run does not. ⚠️ **And `recommendations/` has no tests
  at all** — no test in the repository imports it.~~ ✅ **Both closed 2026-08-06, Phase 7 M2.**
  `services/regeneration.py` turns an accepted recommendation into a new run, and
  `tests/unit/test_recommendations.py` is the first test ever to import `optiedt.recommendations`.

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
   FR-24 and FR-25 stay `—`; `assistant/` stays scaffold-only. *(✅ Superseded by Phase 7, 2026-08-06 —
   all four are built. Kept because it records the decision Phase 6 actually took.)* ADR-010 commits them to increment 1 and
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

**Status. COMPLETE 2026-08-06 — all eight milestones and a closing audit.** **Eight of nine** acceptance criteria were met at Phase 6's close; the ninth needed a person and was settled on 2026-08-07 (reworded — see the header of this file). ⚠️ **Increment 1 was not complete with Phase 6** — Phase 7 followed.

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

**The one that remained** at Phase 6's close was the timed FR-2 walkthrough, which needed a person and
was M6's. It was run on 2026-08-07 — and, like criterion 5 below, **reworded rather than met as
written**, because no time was measured.

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
accepted criterion whose wording does not fit what was built. It was left **unticked** until decided,
because that was the conservative reading — ✅ **and it was decided on 2026-08-05: the criterion was
reworded to carry the limit and is now ticked** (`docs/status.md`). The evidence is above and in the
tests, which encode **both** outcomes — writing only the area case would have let the suite report a
capability the product does not have.

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

### Phase 7 — Regeneration and the assistant · ✅ **complete 2026-08-06** · unbudgeted

**Purpose.** Close increment 1. FR-22, FR-23, FR-24 and FR-25 were committed by ADR-010 and allocated
to no phase — **C-1**, recorded 2026-07-29, approved as a phase by the project owner on 2026-08-06.

**Completion criteria.** All four requirements reachable and acceptance-tested; degraded mode
verified; H10 executing rather than refusing.

| # | Milestone | State |
|---|---|---|
| **M0** | **C-19, C-20, C-21 recorded** in `open-questions.md` with their reasoning, before any code | ✅ **done 2026-08-06** — and it corrected a section heading that had been stale for two phases |
| **M1** | **H10 made live** — `SolverInput` carries `frozenset[Placement]`; a Phase 2 contract change | ✅ **done 2026-08-06**, 13 tests, verified against the real solver by locking all 218 placements |
| **M2** | **Regeneration (FR-23)** — `services/regeneration.py`, the endpoint, the panel, the first tests `recommendations/` has ever had | ✅ **done 2026-08-06**, 49 backend + 11 frontend, an eleventh import contract, and a migration guard |
| **M3** | **Assistant core (FR-22)** — adapter, context builder, verifier, computed forms | ✅ **done 2026-08-06**, 39 tests, and one of them found a real hole in the grounding check |
| **M4** | **Panel and questions (FR-24)** | ✅ **done 2026-08-06**, 9 backend + 10 frontend; verified in the running application |
| **M5** | **The report (FR-25)** — the pre-decided first scope cut, delivered rather than cut | ✅ **done 2026-08-06**, 10 tests |
| **M6** | **Degraded mode, documentation, closing audit** | ✅ **done 2026-08-06** |

**What Phase 7 delivered, in one line each.**

- **FR-23 `✓`** — an accepted recommendation changes one solver input and launches a **new run**;
  overrides **compose** along a chain; the origin run is byte-identical afterwards (invariant 6).
- **FR-22 `✓`** — an explanation from computed figures, with every number checked against the context.
- **FR-25 `✓`** — a report carrying the run's parameters, every candidate and the published one.
- **FR-24 `✓` since 2026-08-07** — built and acceptance-tested in Phase 7, then held at `WIP` by
  **C-21** (no test can establish that a real provider answers well) until the live call that C-21
  always said was the only way to close it: `demonstration.md` §4.
- **H10 executes**, so all twelve hard rules now run. FR-3 lost one of its two stated reasons.

#### The closing audit, 2026-08-06

⚠️ **Its scope was named before it started** — that is Phase 6's lesson applied: *a checklist that
omits a file cannot notice the file*. In scope: `CLAUDE.md`, `README.md`, all 13 `docs/*.md`, all 11
ADRs, `backend/.importlinter`, `scripts/*.ps1`, and every source docstring making a claim about the
system. Same method as Phases 4–6: **compare documents against the repository, never against other
documents.**

| Kind | Found |
|---|---|
| ⚠️ **A row describing the past as the present, in the file read first** | **`dashboard.md`'s "Overall progress" said *"75 % of budgeted effort — Phases 1–4 delivered, Phase 5 is under way"* and *"0 finished"* requirements.** False since 2026-08-04 and 2026-08-06. **Two closing audits missed it**, and Phase 6's fixed the *adjacent* API·frontend row for exactly this fault — so the method was right, applied, and stopped one row short |
| **A signature that could not be implemented** | `assistant/interfaces.py` declared `ContextBuilder.build(kind, run_id)`. Looking a run up needs a store, which is the database — **the signature and invariant 4 could not both be honoured.** The scaffold had encoded an impossible contract, and nothing noticed because nothing implemented it |
| **A guard with a hole, found by a test rather than by review** | The grounding check's number pattern matched at most three ungrouped digits, so **`4271` matched nothing at all** and passed as grounded. Any ungrouped number above 999 — exactly the range an invented count of minutes or periods falls in |
| **A figure reading two ways on one page** | S6's raw value printed as `1.9183673469387754` in the assistant's computed form beside `1.92` in the comparison table. **Found by opening the running application**, which no test did |
| **A test fixture that was not a migration** | `test_store_contract.py` built its schema with `create_all`, which leaves an existing table exactly as it found it. The first added column broke all 38 database tests against a database that had been correct the day before |
| **An accessible name stolen by a spacer** | A `<label>` carrying only whitespace became a button's accessible name. Found by a display test that could not locate the button |

**What the audit did not find:** any architecture violation (**11/11 contracts kept throughout**), any
`TODO` in source, any broken module path, any error in `open-questions.md`'s bookkeeping (**twenty
codes, C-1 to C-21 with no C-10, two open and eighteen resolved**), and no acceptance criterion marked
wrongly.

⚠️ **The lesson Phase 7 adds.** Phases 4–6 established *compare against the repository* and *name the
documents in scope*. This one adds: **the repository includes the running application.** Two of the
six findings above — the double-rendered figure and the stolen accessible name — are invisible to
every form of reading, and one of them is in the file a reader opens first. A document can be checked
against code; a screen can only be checked by looking at it.

### Increment 2 — conditional on remaining time

Examination session (4 d) · weight adjustment from recorded comparisons (3 d). Natural-language
constraint entry is **not undertaken** — see `docs/ai-integration.md`.

---

## Where to look for what

| You need | Read |
|---|---|
| **"What phase are we in?" · what is left before Phase N** | [`docs/project-roadmap.md`](project-roadmap.md) — **the continuous phase view**, Phase 1 to the final phase, with increment 1 and increment 2 mapped into it |
| Invariants, commands, conventions | `CLAUDE.md` |
| Detailed state, measurements, acceptance criteria | [`docs/status.md`](status.md) |
| What is undecided | [`docs/open-questions.md`](open-questions.md) |
| Why a past decision was taken | [`docs/decisions/`](decisions/) — 11 ADRs |
| What happened, session by session | [`docs/history.md`](history.md) — archive, read only for forensics |
| "Is FR-15 built?" | [`docs/requirements-traceability.md`](requirements-traceability.md) |
| How the engine is validated, and against what | [`docs/testing-strategy.md`](testing-strategy.md) |
| Everything else | The table in `CLAUDE.md` |