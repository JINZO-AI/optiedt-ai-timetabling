# OptiEDT — Dashboard

**The handoff file. Read this second, after `CLAUDE.md`.** It carries the whole project state; every
other document is detail you fetch only when you need it.

**Last updated 2026-07-30**, after Phase 2 was completed, committed and pushed.

---

## At a glance

| | |
|---|---|
| **Project** | OptiEDT — generates, ranks and explains weekly university timetables (Tunisian public faculty, LMD) |
| **Overall progress** | **40 % of budgeted effort** (8 of 20 days: Phases 1–2 done). By *delivered product* it is lower — **1 of 9 acceptance criteria** met, 0 of 25 requirements finished, because the user-facing path is Phases 4–5. Both numbers are real; quote the measure with the number |
| **Current phase** | **Phase 3 — not started.** Phase 2 closed 2026-07-30 |
| **Current milestone** | Several candidates produced, ordered, and one difference decomposed |
| **Current goal** | Resolve **C-4** and **C-12**, then encode the objective and the scoring layer |
| **Next task** | ⛔ **Blocked — a specification decision, not a keyboard one.** See "Phase 3 brief" below |
| **Branch** | `main`, in sync with `origin/main` |
| **Latest commit** | [`0dc0078`](https://github.com/JINZO-AI/optiedt-ai-timetabling/commit/0dc0078) — *Repair the infeasible reference instance and resolve C-7* |
| **Repository status** | Clean. 15 commits, nothing uncommitted, nothing unpushed |
| **Project health** | 🟢 **Green.** No known defect, no failing check, no unresolved blocker inside Phase 2 |

```
Increment 1   ████████░░░░░░░░░░░░  40 % of budgeted days

Phase 1  Needs, specification, instance verification   ████████████████████  ✅ done
Phase 2  Modelling H1–H12, first valid timetable       ████████████████████  ✅ done
Phase 3  Score, ranking, portfolio, recommendations    ░░░░░░░░░░░░░░░░░░░░  ⏳ blocked on C-4, C-12
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
| **Solver** | 🟢 H1–H12 built and demonstrated correct. Reference instance solves in **2.8–3.3 s** (deterministic 0.13–0.21) across 7 seeds, all 218 sessions placed. C-7 accounting (`x[s,t₀]`, `y[s,t]`) built and tested, off by default |
| **Objective** | ⛔ Not encoded. Blocked on C-4 — no soft criterion has a formula |
| **Analysis / scoring** | ⛔ Interfaces only, no implementation. Phase 3 |
| **API · frontend · persistence** | ⬜ Scaffold only. Phases 4–5. The solver reads CSVs through `optiedt.instance`; PostgreSQL is not needed until runs must survive a restart |
| **Assistant** | ⬜ Scaffold only. Increment 1 (ADR-010), Phase 4+ |
| **Validation** | 🟢 `scripts/run-checks.ps1` green: 7/7 contracts · ruff · format · mypy strict on 32 files · tests · instance verification · frontend `tsc` |
| **Tests** | 🟢 **33 passing** (29 fast + 4 solver-marked). Fast path 1.7 s, full suite 14 s |
| **Documentation** | 🟢 Current as of this commit. Session history archived to `docs/history.md` |

---

## Open questions

**[`docs/open-questions.md`](open-questions.md) is the authority — this is a summary of it.** If the two
ever disagree, that file wins and this table is the bug. **Do not silently decide one.**

| # | Open question | Blocks | Owner |
|---|---|---|---|
| **C-4** | `v_i` and `min_i`/`max_i` undefined for **all seven** soft criteria | **Phase 3 — everything** | Technical lead |
| **C-12** | S5 carries weight 0.20 and has **no input data** — no "preferred" state in the schema | Phase 3, Phase 4 grid | Technical lead |
| **C-5** | "At least three candidates" can fail when duplicates are removed | Phase 6 acceptance | Lead + supervisor |
| **C-9** | FR-6, FR-10, FR-17, FR-18 have no detailed specification | Phase 6 acceptance | Technical lead |

**Resolved, do not reopen without new evidence:** C-1, C-2, C-3, C-6, C-7, C-8, C-11, C-13.

⚠️ **C-12 and C-5 are one bug waiting to happen.** The teacher-favouring profile differs by raising S3
*and* S5. If S5 measures identically zero it differs by S3 alone, two candidates converge, duplicate
removal drops one, and the three-candidate acceptance test fails — for a reason nobody would look for,
because the symptom is "the portfolio is boring" and the cause is a missing column.

---

## Known risks

| Risk | Effect | Handling |
|---|---|---|
| **C-12 × C-5 interaction** | Acceptance test fails for an invisible reason | Resolve C-12 *before* Phase 3 |
| **~2.5 unbudgeted assistant days** | ≈12 % overrun on 20 days | Confirmed, not contingent. Release valve is scope-reduction step 1 |
| **91 % laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and an infeasible instance looks like a slow model** | Pre-analysis first, always. Read the *window* figure, not the period figure |
| **A check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is blamed on the model. Cost three sessions on C-13 | Both bounds now checked. **FR-12's port must carry both** |
| **Objective auxiliaries uncounted** | Model size is an underestimate | Follows from C-4; recorded as unknown rather than guessed |
| **Deterministic-time calibration unmeasured** | The user-facing time limit is a guess | Dormant — solves take ~0.2 units. Live again when the objective lengthens them |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |

---

## Roadmap — remaining phases

### Phase 3 — Score, ranking, portfolio, recommendations · ⏳ **next, blocked**

**Purpose.** Turn one valid timetable into *several*, ordered, with the difference between any two
explained term by term. This is the half of the product that makes it defensible rather than merely
automatic.

**Completion criteria.**
- Three weight profiles produce candidates; each carries an overall score /100 and its sub-scores.
- The displayed contributions **sum exactly** to the score difference, to display precision.
- Dominance is detected and reported.
- Two runs with the same data, weights and seed produce identical candidates in the same order.

**Dependencies.** ⛔ **C-4** (formulas + bounds for all seven criteria) and **C-12** (S5 has no data).
Neither can be decided at the keyboard. Phase 2 is otherwise a complete foundation.

**Status.** Not started. Interfaces exist (`analysis/interfaces.py`, the `Criterion` Protocol); the
solver-side variables the objective will read (`x[s,t₀]`, `y[s,t]`) are built and tested.

### Phase 4 — Web interface · ⬜ 4 days

**Purpose.** The complete path from a teacher declaring availability to a published timetable.
**Completion criteria.** Availability grid filled in under 5 minutes without training; generation
screen; side-by-side comparison with contributions; timetable views by teacher, group, room, lab.
**Dependencies.** Phase 3 (there is nothing to compare until candidates are scored). Also **C-12** —
the grid needs a three-state cell if "preferred" becomes real data.
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

## Phase 3 brief — read this before starting Phase 3

**What it is trying to achieve.** A *portfolio*, not a timetable. Several valid timetables produced
under different weight profiles, ranked by an exact weighted sum, with the difference between any two
decomposed criterion by criterion.

**Why it exists.** The department will not adopt a timetable it cannot argue with. The score is linear
precisely so the explanation *is* the calculation read term by term, recomputable by hand from the
sub-scores and weights recorded with the run. That is the whole reason a weighted sum was chosen over
lexicographic ordering or a learned ranker (ADR-002).

**⛔ Solve these first — they are not keyboard decisions.**

1. **C-4** — define `v_i` *and* `min_i`/`max_i` for S2, S3, S4, S5, S6, S7, S10. One task per criterion,
   not two: the `Criterion` Protocol requires `raw_value` and `bounds` together so a criterion cannot be
   half-defined. S6 has a dead half — H5 already forbids a room smaller than its group, so "over-used"
   must mean utilisation rate; the documents never say.
2. **C-12** — decide whether S5 gets real data (a third availability state), a proxy definition, or is
   accepted as measuring zero. Option (c) is cheapest and most dangerous; see the warning above.

**Which documents are authoritative.**

| Question | Authority |
|---|---|
| The three formulas, bounds policy, the four required properties | [`docs/scoring-and-explanation.md`](scoring-and-explanation.md) |
| Criterion codes, names, default weights | `data/instance/constraint_catalogue.csv` — **not** the PDFs |
| Which variables the objective may read | [`docs/constraint-model.md`](constraint-model.md), C-7 section |
| Layer permissions | [`docs/architecture.md`](architecture.md) + `backend/.importlinter` |
| Recommendations and regeneration | [`docs/ai-integration.md`](ai-integration.md) |

**Files expected to change.** `analysis/` (criteria, scoring, ranking, decomposition, dominance —
currently interfaces only) · `solver/objective.py` (new; reads `x`/`y` from `solver/occupancy.py`) ·
`solver/engine.py` (call `build_occupancy` and post the objective when a profile carries weights) ·
`recommendations/` (the closed 3-action catalogue) · `tests/property/` (the four analysis properties) ·
`data/instance/constraint_catalogue.csv` if C-12 adds a column.

**Constraints already implemented.** All twelve hard constraints. H1, H3, H7, H12 are real CP-SAT
postings and carry assumption literals; H4, H5, H6, H8, H9, H10 are domain restrictions applied at
variable construction; H2 is subsumed by H12 and H11 by H3, both registered as documented no-ops.
**H10 is registered but dormant** — `build_variables` refuses to run if any session is locked, because
there is no way yet to supply the target slot/room. The reference instance has no locked sessions.
Filling that gap is Phase 3 work, since recommendation-driven regeneration is what first needs it.

**Constraints remaining.** None for the weekly model. The seven soft criteria S2–S10 are *criteria*,
not constraints, and none is implemented. X1–X4 and SX1 are the examination model — increment 2.

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
