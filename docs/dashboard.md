# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-07-31. Phase 3 is COMPLETE.** Validation on the published ITC-2007 instances closed
the last item; before it, portfolio orchestration and FR-16 landed, ADR-011's overdue calibration was
discharged and the ADR amended, C-16 was raised and resolved (`interleave_search`), and C-15 was
deferred by decision. **Phase 4 — the web interface — has not started.**

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **~70 % of budgeted effort** — Phases 1–3 complete and Phase 4 at 5 of 6 milestones, ~15 of 20 days budgeted. By *delivered product*: **4 of 9 acceptance criteria** met (the displayed-contributions criterion fell in Phase 4 M5), 0 of 25 requirements finished, because a requirement is `✓` only once a user can reach it *and* it is tested end to end. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 4 — the web interface. IN PROGRESS, M5 of 6 complete.** Generation, the four timetable views and the comparison screen all run end to end against the real solver. **Blocked on two decisions** — see the milestone table below |
| **Last completed phase** | **Phase 3 — COMPLETE 2026-07-31.** Criteria, scoring, ranking, decomposition, dominance, the objective, the recommendation translator, the **portfolio**, **FR-16** and **validation on the 21 published ITC-2007 instances** are all implemented and tested; ADR-011's calibration is discharged |
| **Milestone reached** | Phase 3's: several candidates produced, ordered, and one difference decomposed — met **at the code level**; not yet reachable by a user (no run record, no endpoint). Phase 4's milestone is the complete path from declaring availability to publication |
| **Current goal** | Deliver Phase 4: the complete path from a teacher declaring availability to a published timetable |
| **Next task** | ⚠️ **Blocked on two decisions, both the technical lead's.** **C-12(a)** — two- or three-state cell — must be settled before M6's availability grid, the last milestone. **C-14** must be settled before M5's dominance signal, which is the only part of the comparison screen left unbuilt. Nothing else in Phase 4 is outstanding |
| **Branch** | `main` — ahead of `origin/main` by unpushed local commits. **No count is recorded here**, deliberately: `git rev-list --count origin/main..HEAD` |
| **Latest commit** | **Not recorded here** — it is stale the moment anything is committed. `git log -1 --oneline`. The durable fact is the last *pushed* commit, in the row below |
| **Repository status** | Last pushed: `origin/main` at [`bfe805a`](https://github.com/JINZO-AI/optiedt-ai-timetabling/commit/bfe805a), 2026-08-01. Everything after it is local. ⚠️ **This row has been wrong three times.** `0dc0078` (a *parent* commit) until 2026-07-31; `acf9aa0` with "9 commits ahead" until 2026-08-01, by which time eight of the nine were pushed; then "1 commit ahead" — which the very commit correcting it made 2. **A commit count cannot live in a file that commits change.** Record the pushed SHA, re-derive the rest: `git rev-parse origin/main` |
| **Project health** | 🟢 **Green.** `scripts/run-checks.ps1` green, **125 tests** pass, 8/8 layer contracts kept. **C-16 resolved** — reproducibility and three distinct candidates hold simultaneously at production settings, and the portfolio is ~2× faster than before. **3 of 9 acceptance criteria met**, up from 1. The engine is validated on all 21 published ITC-2007 instances |

```
Increment 1   ███████████░░░░░░░░░  55 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ████████████████████  ✅ done
Phase 4  Web interface — grid, generation, comparison  ░░░░░░░░░░░░░░░░░░░░  ⬜ not started  ← next
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
Phase 6  Tests, documentation, presentation            ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
```

*Progress is measured in delivered phases against the 20-day increment-1 plan (Phase 1 = 3 d,
2 = 5 d, 3 = 3 d, 4 = 4 d, 5 = 2 d, 6 = 3 d). Phases 1–3 = 11 of 20 days budgeted, delivered in ~3.*

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **9/9 contracts kept**. No layer edge has been weakened; the count has only ever gone up. The eighth (2026-07-31) keeps the ITC-2007 harness out of the product; the ninth (Phase 4 M1) keeps `api` off the solver. Both were verified to fire before being relied on |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 fully closed — accounting (`x[s,t₀]`, `y[s,t]`) built on demand, auxiliaries measured at **5,249**. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions; `engine.py` posts it — and builds occupancy at all — only when a criterion carries weight, so an all-zero profile is genuinely equivalent to a feasibility solve. **Deterministic budget calibrated 2026-07-30** — it binds exactly, per worker; 1 unit ≈ 4.8 s wall at one worker, ≈ 19 s at all sixteen. **`interleave_search = true` is set and is required for reproducibility** (C-16, ADR-011 amended); the warm start is withheld when an objective is posted, because it pinned all three profiles to one timetable |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance/**recommend** — FR-16). **The four properties the specification requires** (`docs/scoring-and-explanation.md`) all pass, verified by **ten** hypothesis tests in `tests/property/test_scoring_properties.py` — four specified, ten tests; the extra six cover edge cases the four imply but do not state |
| **Portfolio** | 🟢 `services/portfolio.py` — the only module importing both `solver` and `analysis`, which is what `services` is for. Defines the three profiles, divides the total budget between them, solves sequentially under one fixed seed, removes duplicate timetables and ranks the survivors under one weight vector. 16 unit tests pin the rules against a recording fake solver. Measured on the reference instance: **3 distinct candidates in 147–150 s**, reproducibly, total budget 90 (C-16) |
| **API · frontend · persistence** | 🟡 **API complete for Phase 4 (M1–M2); generation and the four timetable views work (M3–M4); comparison and the availability grid remain.** React shell with `react-router` and `@tanstack/react-query`; `features/generation` launches a run, polls it and renders the ranked candidates with all seven sub-scores; `features/timetable` shows a candidate by teacher, group, room and as room occupancy (FR-7, FR-18). **A group's view includes its ancestors' sessions** — a CM gathers the whole promotion, so a subgroup shown only its own sessions would display a week with holes its students do not have. ⚠️ **The frontend computes nothing** — no score, no re-normalisation, no sorting; rank order is the array order the API returns (`docs/architecture.md`: the presentation layer may not "compute a score, decide an order"). Ten endpoints under `/api`, which `vite.config.ts` already proxies: the instance, FR-2's availability read/write, `POST /runs` → **202** with polling on `GET /runs/{id}`, and the candidate, comparison, dominance and recommendation reads. `tasks/executor.py` runs solves in-process on a **single-worker pool** (ADR-005) — one solve at a time, because each already uses every core. Both stores are **in memory** behind Protocols; Phase 5 substitutes database-backed ones with no router change. A ninth import contract, `api ⇸ solver`, was added and verified to fire. PostgreSQL is not needed until runs must survive a restart |
| **Assistant** | ⬜ Scaffold only. Increment 1 (ADR-010), Phase 4+ |
| **Validation** | 🟢 `scripts/run-checks.ps1` green, **ten steps**: **9/9 contracts** · ruff · format · mypy strict on 59 files · 168 backend tests · instance verification · frontend `tsc` · **frontend tests** (added M5). `pytest` exit 5 is **no longer tolerated** (Phase 4 M1) — with 168 tests collected, allowing "collected nothing" would let a broken import pass as success. Separately, `scripts/validate-itc2007.ps1` runs the engine against the 21 published ITC-2007 instances — not in `run-checks` because a full sweep takes tens of minutes |
| **Tests** | 🟢 **168 backend** (146 fast + 22 solver-marked) **+ 7 frontend**. The frontend tests are new in Phase 4 M5 (`vitest` + `@testing-library/react`) and `run-checks.ps1` runs them: they assert on **rendered** figures, which `tsc` cannot, and the acceptance criterion is about what is *displayed*. They caught a real rounding defect on their first run. Phase 4 also added `tests/unit/test_api_schemas.py` (the wire format: French enum literals, camelCase fields — the guard against the `RoomType` defect returning), `tests/unit/test_availability_api.py` (FR-2's replace-wholesale rule and the `SYNTHETIC`/`TEACHER` distinction), `tests/unit/test_run_lifecycle.py` (the state machine, including that `DIAGNOSING` is reachable only from `INFEASIBLE`) and `tests/integration/test_api_runs.py` (the run endpoints against a **fake solver**, so they stay in the fast suite and carry no timing assumption — the test waits on the executor's Future). Phase 3's 125 are unchanged. New in Phase 3: `tests/integration/test_reproducibility.py` (FR-19/ADR-011 — reproducibility **at production settings**, and the per-worker budget binding), `tests/property/test_scoring_properties.py` (10 hypothesis properties), `tests/unit/test_criteria.py` (the seven formulas against a hand-computable instance), `tests/integration/test_objective_matches_analysis.py` (**the cross-layer guard** — CP-SAT's objective value must equal the analysis layer's recomputation on the same placements), `tests/unit/test_portfolio.py` (16 orchestration rules against a recording fake solver), `tests/unit/test_recommendation.py` (FR-16, including the proof that a dominated candidate can never be recommended), `tests/unit/test_itc2007_cost.py` and `tests/integration/test_itc2007_validation.py` (ITC-2007's rules against hand-computed values, and against seven solutions the archive publishes) |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |
| **C-14** | Dominance uses the strict reading ("improves on **every** criterion"); S10's zero weight makes ties common. **And the "dominated *top* candidate" signal both documents require is provably unreachable** — a dominated candidate cannot outscore its dominator, so it can never rank first. Phase 4 would otherwise build a signal that can never fire | Phase 4 comparison screen | Technical lead |
| **C-15** | The objective weights raw violation counts of incomparable scale, so "teacher-favouring" favours only S5, not S3. **Deferred by decision 2026-07-30** — recorded, objective unchanged | FR-13's `✓`; Phase 4 comparison screen | Technical lead |

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
  candidates, agreeing to 9 decimal places. The acceptance criterion stays unticked because *displayed*
  needs Phase 4's comparison screen.
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

### Phase 4 — Web interface · ⬜ 4 days · **next**

**Purpose.** The complete path from a teacher declaring availability to a published timetable.
**Completion criteria.** Availability grid filled in under 5 minutes without training; generation
screen; side-by-side comparison with contributions; timetable views by teacher, group, room, lab.
**Dependencies.** Phase 3 is complete and its algorithms — score, ranking, decomposition, dominance,
the recommendation rule and the portfolio — exist to build the screens on. Persistence of runs and
candidates is Phase 5 and will most likely be built alongside this phase's `services`/`db` work rather
than as a separate pass. Two open questions land here: **C-14**, which must be settled before the
comparison screen builds a dominance signal that can never fire, and **C-12** — the availability grid
needs a three-state cell if a real preferred-window column (option (a), not yet built) is added.

**Status. IN PROGRESS — M1 of 6 complete.** Six milestones, in this order:

| # | Milestone | State |
|---|---|---|
| **M1** | API foundation — `GET /api/instance`, FR-2 availability read/write, wire format pinned | ✅ **done** |
| **M2** | Run lifecycle — `services/runs.py`, `tasks/executor.py`, `POST /runs` → 202, polling, candidate/comparison/dominance/recommendation endpoints | ✅ **done** |
| **M3** | Frontend shell + generation screen (FR-13, FR-5, FR-6) — **verified end to end against the real solver** | ✅ **done** |
| **M4** | Timetable views (FR-7, FR-18) — by teacher, group, room, plus room occupancy | ✅ **done** |
| **M5** | Comparison screen (FR-14, FR-15) — **ticks acceptance criterion 3**. ⚠️ Dominance signal deliberately NOT built, held for **C-14** | ✅ **done, minus the blocked part** |
| **M6** | Availability grid (FR-2) — ⚠️ cell model needs **C-12(a)** | ⬜ |

⚠️ **Scope note, stated rather than assumed.** Phase 4 is written as "the web interface", but no screen
can exist without an API, and this block already anticipated it ("built alongside this phase's
`services`/`db` work"). Phase 4 therefore delivers **the screens plus the minimum API to reach them,
with the run store in memory**. Authentication and RBAC (FR-11), PostgreSQL and the diagnosis run stay
in Phase 5. **The API has no authentication yet and must not be exposed beyond a development machine.**

### Phase 5 — Pre-analysis in-app, diagnosis, auth, run record · ⬜ 2 days

**Purpose.** An infeasible instance must produce a report naming the rules in conflict, not a
timeout; every published timetable must trace back to its run, seed and weights.
**Completion criteria.** FR-12 reports structural risks through the API; the diagnosis run returns a
sufficient conflict set; a teacher account sees only its own data; runs are recorded.
**Dependencies.** Phase 3 for the run record; C-6 is already resolved (only H1, H3, H7, H12 carry an
assumption literal, so the conflict report can name an actionable rule).
⚠️ **FR-12 must port the contiguity bound as well as the period bound** — shipping the period bound
alone would put the C-13 blind spot inside the product.
**Status.** Not started. `preanalysis/` has the Protocol and the five check names, no bodies. The
working logic already exists in `data/verification/verify_instance.py`.

### Phase 6 — Tests, documentation, presentation · ⬜ 3 days

**Purpose.** Acceptance requirement by requirement; the project is accepted that way.
**Completion criteria.** The nine acceptance criteria in `docs/status.md` all ticked; documents complete.
**Dependencies.** All previous phases. **C-5** and **C-9** must be settled before the acceptance tests
are written, or they will fail for reasons that are not defects.
**Also lands here.** The **instance generator** (`data/generator/`), a stated PPM §10 deliverable that
does not exist — item 9 of `docs/status.md`'s "Next, in order". It must reproduce *the* documented
instance, not merely a valid one (ADR-008).
**Status.** Not started. **Three of nine** acceptance criteria are met.

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
