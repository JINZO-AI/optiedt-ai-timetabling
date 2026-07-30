# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-07-30**, after Phase 3's core algorithms were implemented and tested (C-4 and C-12
resolved the same session).

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **~55 % of budgeted effort** (Phases 1–2 = 8 of 20 days, plus Phase 3's 3 days of core algorithm work). By *delivered product* it is lower — **1 of 9 acceptance criteria** met, 0 of 25 requirements finished, because the user-facing path is Phases 4–5. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 3 — core algorithms done, integration remains.** Criteria, scoring, ranking, decomposition, dominance, the CP-SAT objective and the recommendation translator are implemented and tested. Portfolio orchestration (loop over the 3 profiles, remove duplicates), persistence and ITC-2007 validation are not — those need `services`/`db`, Phases 4–5 |
| **Current milestone** | Several candidates produced, ordered, and one difference decomposed — met **at the code level**; not yet reachable by a user (no run record, no endpoint) |
| **Current goal** | Phase 4: the web interface — availability grid, generation screen, comparison screen |
| **Next task** | Port the five pre-analysis checks into the application (FR-12), **or** start Phase 4. Neither is blocked |
| **Branch** | `main`, in sync with `origin/main` |
| **Latest commit** | [`0dc0078`](https://github.com/JINZO-AI/optiedt-ai-timetabling/commit/0dc0078) — *Repair the infeasible reference instance and resolve C-7*. Phase 3's commit is not yet pushed |
| **Repository status** | Phase 3 changes committed locally, not pushed. 15 commits on `origin/main`, plus this session's work |
| **Project health** | 🟢 **Green.** No known defect, no failing check. `scripts/run-checks.ps1` green including the new property tests |

```
Increment 1   ███████████░░░░░░░░░  ~55 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ███████████████░░░░░  🟡 core algorithms done; portfolio orchestration + persistence + ITC-2007 validation remain
Phase 4  Web interface — grid, generation, comparison  ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
Phase 5  Pre-analysis in-app, diagnosis, auth, runs    ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
Phase 6  Tests, documentation, presentation            ░░░░░░░░░░░░░░░░░░░░  ⬜ not started
```

*Progress is measured in delivered phases against the 20-day increment-1 plan (Phase 1 = 3 d,
2 = 5 d, 3 = 3 d, 4 = 4 d, 5 = 2 d, 6 = 3 d). Phases 1–2 = 8 of 20 days budgeted, delivered in ~2.*

---

## Status by area

| Area | State |
|---|---|
| **Architecture** | 🟢 Stable. Four layers, boundaries enforced by `import-linter` — **7/7 contracts kept**. No layer edge has been weakened |
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 accounting (`x[s,t₀]`, `y[s,t]`) built and tested, called on demand. `solver/objective.py` (new) encodes S2–S10 as CP-SAT expressions and is posted by `engine.py` whenever `request.profile is not None`; a real solve under the catalogue's default weights takes ~50 s wall / ~92 deterministic units on this machine (up from ~3 s / ~0.2 with no objective — the "live again once solves get long enough" risk below is now live) |
| **Objective** | 🟡 Encoded for S2–S5, S7, S10 in full; **S6 only for non-cumulative room types** (Salle) — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable to optimise against, only a post-hoc labeller (C-13). `analysis/criteria.py` still scores S6 correctly for every room after the fact |
| **Analysis / scoring** | 🟢 Implemented and tested. `analysis/criteria.py` (7 criteria), `analysis/scoring.py` (`DefaultScorer`, `evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker`: rank/decompose/dominance). All four properties pass (`tests/property/test_scoring_properties.py`). Not yet wired to a run/portfolio orchestration — that is `services/`, Phase 4–5 |
| **API · frontend · persistence** | ⬜ Scaffold only. Phases 4–5. The solver reads CSVs through `optiedt.instance`; PostgreSQL is not needed until runs must survive a restart |
| **Assistant** | ⬜ Scaffold only. Increment 1 (ADR-010), Phase 4+ |
| **Validation** | 🟢 `scripts/run-checks.ps1` green: 7/7 contracts · ruff · format · mypy strict on 32 files · tests · instance verification · frontend `tsc` |
| **Tests** | 🟢 **39 passing** (35 fast + 4 solver-marked). New: `tests/property/test_scoring_properties.py`, 5 hypothesis-based tests for the four analysis properties |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |

**Resolved, do not reopen without new evidence:** C-1, C-2, C-3, C-6, C-7, C-8, C-11, C-13, **C-4, C-12**
(2026-07-30 — formulas for all seven criteria; S5 via a labeled edge-of-day proxy, see
`docs/open-questions.md`).

⚠️ **C-5 is still open.** Resolving C-12 lowers the chance of hitting it on the reference instance (S5
now varies with the candidate instead of measuring zero), but does not resolve the specification's own
conflict between "duplicates removed" and "at least three candidates". Settle it before writing the
FR-13 acceptance test.

---

## Known risks

| Risk | Effect | Handling |
|---|---|---|
| **~2.5 unbudgeted assistant days** | ≈12 % overrun on 20 days | Confirmed, not contingent. Release valve is scope-reduction step 1 |
| **91 % laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and an infeasible instance looks like a slow model** | Pre-analysis first, always. Read the *window* figure, not the period figure |
| **A check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is blamed on the model. Cost three sessions on C-13 | Both bounds now checked. **FR-12's port must carry both** |
| **Deterministic-time calibration is now live, not dormant** | A real solve with the objective on took ~92 deterministic units / ~50 s wall against a 30 s deterministic budget under `num_workers=0` — the same under-bounding C-2/C-13 measured, now actually reached because the objective lengthens solves as predicted | Not recalibrated this session (out of scope). Measure across seeds/profiles before Phase 4 exposes a user-facing time limit |
| **S6 cannot be optimised for cumulative room types** | The CP-SAT objective only covers Salle (non-cumulative); Amphi/Lab_Info/Lab_Sciences rooms are chosen by a post-solve labeller the objective cannot see | Scored correctly after the fact regardless (`analysis/criteria.py`). Closing this needs `solver/variables.py` changes — out of scope this session |
| **`recommendations/translator.py` cannot build a full `SolverInput`** | `Run`/`Candidate` carry no instance reference, no base profile weights, no prior locks/exclusions | Returns a `RunOverride` (plain domain data) instead; a later layer (`services/`, Phase 4–5) must assemble the actual `SolverInput` |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |

---

## Roadmap — remaining phases

### Phase 3 — Score, ranking, portfolio, recommendations · 🟡 **core algorithms done, integration remains**

**Purpose.** Turn one valid timetable into *several*, ordered, with the difference between any two
explained term by term. This is the half of the product that makes it defensible rather than merely
automatic.

**Completion criteria.**
- Three weight profiles produce candidates; each carries an overall score /100 and its sub-scores.
  ⬜ **Not yet** — the objective accepts any one profile and a solve under it produces a scored
  candidate, but nothing loops over 3 profiles and deduplicates yet; that is `services/`, Phase 4–5.
- The displayed contributions **sum exactly** to the score difference, to display precision. ✅ **Met**
  at the code level — `analysis/ranking.py`'s `decompose()`, verified by
  `tests/property/test_scoring_properties.py::test_decomposition_is_exact`.
- Dominance is detected and reported. ✅ **Met** — `DefaultRanker.dominance()`, property-tested.
- Two runs with the same data, weights and seed produce identical candidates in the same order.
  🟡 **Solver-side reproducibility is Phase 2's ADR-011 treatment, unchanged**; scoring/ranking are pure
  functions of the placements, so determinism follows once the solve itself is deterministic. Not
  independently re-measured with the objective posted this session — see the deterministic-time risk
  above.

**Dependencies.** ✅ **C-4** and **C-12** resolved 2026-07-30 — see `docs/open-questions.md` for the
formulas and reasoning. Phase 2 was otherwise a complete foundation.

**Status.** `analysis/criteria.py` (S2–S7, S10), `analysis/scoring.py`, `analysis/ranking.py`,
`solver/objective.py` (new), `recommendations/translator.py` (new) are implemented and tested — see
"Status by area" above for what each one does and does not yet cover (S6's cumulative-room-type gap,
the translator's inability to build a full `SolverInput`). **Not done:** portfolio orchestration (loop
over profiles, remove duplicates — needs C-5 decided first, see above), persistence of runs/candidates,
validation on the published ITC-2007 instances, H10's target-slot/room gap in `solver/variables.py`.

### Phase 4 — Web interface · ⬜ 4 days

**Purpose.** The complete path from a teacher declaring availability to a published timetable.
**Completion criteria.** Availability grid filled in under 5 minutes without training; generation
screen; side-by-side comparison with contributions; timetable views by teacher, group, room, lab.
**Dependencies.** Phase 3's algorithms exist to compare against; the portfolio orchestration and
persistence Phase 3 left undone will most likely be built as part of this phase's `services`/`db` work
rather than a separate pass. Also **C-12** — the grid needs a three-state cell if a real preferred-window
column (option (a), not yet built) is added.
**Status.** Not started. React + Vite scaffold only.

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
**Status.** Not started. One of nine acceptance criteria is met.

### Increment 2 — conditional on remaining time

Examination session (4 d) · weight adjustment from recorded comparisons (3 d). Natural-language
constraint entry is **not undertaken** — see `docs/ai-integration.md`.

---

## Phase 3 — what was built 2026-07-30, and what Phase 4 inherits

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

**Built, this session.** `analysis/instance_view.py` (shared hierarchy/day-period lookups),
`analysis/criteria.py` (the seven `Criterion` implementations), `analysis/scoring.py` (`DefaultScorer`,
`evaluate_candidate`), `analysis/ranking.py` (`DefaultRanker` — rank/decompose/dominance),
`solver/objective.py` (new — the same seven formulas as CP-SAT expressions), `solver/engine.py` (wired
to call `build_occupancy` + the objective when `request.profile is not None`),
`recommendations/translator.py` (new), `tests/property/test_scoring_properties.py` (the four
properties, hypothesis-based).

**Not built, and why.** Portfolio orchestration (loop over 3 profiles, remove duplicates) needs **C-5**
decided first — resolving it while candidates could silently converge would just move the risk, not
remove it — and belongs in `services/`, which is out of this pass's scope along with `db/`, `api/`,
`tasks/`. Validation on the published ITC-2007 instances (`docs/testing-strategy.md` §1) was not run
against the new objective. H10's target-slot/room gap in `solver/variables.py` (see Phase 5 origin
below) was **not** closed — closing it needs `solver/variables.py` and `solver/interfaces.py` changes,
both outside `analysis/ · solver/objective.py · recommendations/ · tests/property/`.
`recommendations/translator.py` therefore returns a `RunOverride` (plain domain data), not a
`SolverInput` — see "Known risks" above for why the existing `Run`/`Candidate` schema cannot support
building one directly.

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
| Everything else | The table in `CLAUDE.md` |
