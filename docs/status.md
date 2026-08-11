# Status

**Increment 1 of 2 · Phases 1–11 complete. ✅ INCREMENT 1 IS COMPLETE.** **Phase 11 closed 2026-08-11
and took the requirement count from 16 `✓` to 18 of 25** — FR-9 and FR-11, closed by building the two
surfaces whose mechanisms already existed and were already tested. Phase 10 closed 2026-08-10 and took
it from **10 to 15** — FR-3, FR-4, FR-7, FR-14 and FR-16, each against a criterion the supervisor wrote.
**A pre-Phase-11 audit the same day added FR-17 → 16 of 25** and
**narrowed C-9 from four requirements to two**, on evidence in SRS Table 36 that nobody had checked.
**Nineteen open questions resolved (C-1 to C-21, no C-10). One remains open — C-9, now narrowed to FR-10 and FR-18.** **C-15 was
resolved on 2026-08-07, on measurement, by refuting its own recorded diagnosis** — the objective
formulation is sound and unchanged; `teacher-favouring` now raises S3 and S4. C-19, C-20 and C-21 were decided on 2026-08-06, before any
Phase 7 code: how a locked session's target reaches the solver, where a regeneration assembles its run,
and whether a test may call a live language model.
**Last updated 2026-08-11.**

Keep this file current. A stale status file is worse than none, because the next session trusts it.

> **Read [`docs/dashboard.md`](dashboard.md) first.** It carries the project state, the roadmap and the
> brief for whichever phase is current — **Phase 11, now closed** — in one page. This file is the detail behind it:
> blockers, measurements, phases, acceptance criteria. Session-by-session history is archived in
> [`docs/history.md`](history.md).

---

## Where the project is

| | |
|---|---|
| **Current phase** | **Phase 12 — Data management (FR-1). NOT STARTED, and opening it is the project owner's call.** **Phase 11 — administrative surfaces — closed on 2026-08-11**, taking the count from 16 `✓` to **18 of 25** (FR-9, FR-11). ⚠️ **It was not frontend-only**: six endpoints, a `calendar_overrides` table layered over the pristine instance, `users.group` and one migration. **C-9 is untouched.** Before it, **Phase 10 — requirement closure by test — closed on 2026-08-10**, taking the count from 10 `✓` to **15 of 25** (FR-3, FR-4, FR-7, FR-14, FR-16). ⚠️ **Four of the five had no acceptance criterion either** — SRS Table 35 has no row for FR-4, FR-7, FR-14 or FR-16 — and were closed against their **SRS §3.2** input/processing/output row instead, now transcribed verbatim into `docs/testing-strategy.md` §4. **C-9 is untouched.** Before it, Phase 9 (outputs and distribution, FR-10) closed on 2026-08-10; before it **Phase 8 — increment-1 closure and hardening**, closed at `fa5378c` on 2026-08-07, and **Phase 7 — regeneration and the assistant, COMPLETE 2026-08-06**, all seven milestones and a closing audit. ⚠️ The continuous phase view is [`docs/project-roadmap.md`](project-roadmap.md). **Increment 1 is complete.** **All nine acceptance criteria met**, the ninth on 2026-08-07 — ⚠️ **reworded rather than met as written**, because the run established no time. See the acceptance list at the foot of this file. Milestone table in [`docs/dashboard.md`](dashboard.md) |
| **Last completed phase** | **Phase 11, closed 2026-08-11.** The administrative surfaces: `GET`/`PUT`/`DELETE /api/calendar` and `GET`/`POST`/`DELETE /api/accounts` for the administrator (SRS Table 2 gives that actor both), and `GET /api/me/timetable` for the student — their own group's **published** week, filtered on the server. **80 backend tests and 26 frontend; 17 of 17 mutations detected, two of them only after the tests themselves were repaired.** ⚠️ **One limitation recorded**: the shortened-day window is configured and previewed, and the timetable views still print ordinary hours. Before it, **Phase 10, closed 2026-08-10.** Five acceptance files — `test_fr03` rewritten to cover **all twelve H codes** (it checked seven and mis-numbered two of them), plus new `test_fr04`, `test_fr07`, `test_fr14` and `test_fr16` — and two frontend files for FR-7's display half, which is where the *selection* of a resource's sessions actually lives. **35 backend tests and 18 frontend, and one source file touched: a stale comment.** ⚠️ **Every new assertion was verified to fire by mutating the source first**, and one was found that CANNOT — see the FR-16 note in `docs/requirements-traceability.md`. Before it, **Phase 9, closed 2026-08-10.** FR-10's software: a `@media print` stylesheet with a print-only identity header, and a CSV export carrying the run's whole trace, on all four timetable views and on publications. **Frontend only — no backend file was touched**, because `architecture.md` puts "display, filter, print" in the presentation layer. ⚠️ **FR-10 stayed `WIP`**: C-9 leaves it with no criterion to verify against, so the `✓` count did not move. Before it, **Phase 8, closed 2026-08-07** — the ninth acceptance criterion (FR-2), FR-24's first live provider call, **C-15 resolved on measurement** (FR-13 → `✓`) and the production secret-key guard. ⚠️ **This row named Phase 6 until 2026-08-10**, having missed Phases 7 and 8 entirely — the same fault the dashboard records against itself, in a second file. Before them, **Phase 6, closed 2026-08-06:** eight milestones — the acceptance suite, FR-8/FR-12's tests, FR-9's, the instance generator, the demonstration script and the closing audit; **C-5 and C-14 resolved** by project-owner decision, both recorded before the code. Before it, **Phase 5, closed 2026-08-04.** Six milestones: the five checks in-app (FR-12), the diagnosis run (FR-8), the run record in PostgreSQL (FR-19), authentication and rights (FR-11), publication with its trace, and the closing audit. **C-17 and C-18 resolved**, both recorded before the code. **Two** acceptance criteria moved from unmet to met — ⚠️ **this line said three until 2026-08-05 and was wrong**: four were met at Phase 4's close and the total is six, so M4's teacher scoping and M5's publication trace are the two. The conflict-report criterion is **not** among them; see the acceptance list at the foot of this file. Before it, **Phase 4, closed 2026-08-01.** Six milestones: the API foundation, the run lifecycle and executor, and four screens — availability, generation, timetables, comparison. First frontend tests. C-12(a) resolved and C-14 deferred, both recorded before the code was written. Before it, Phase 3 (closed 2026-07-31) delivered the criteria, scorer, ranker, objective, translator, portfolio and the ITC-2007 validation |
| **Next step** | **Phase 12 — data management (FR-1), and it needs the project owner's approval before it opens.** FR-1 is the last requirement with no software outside the two conditional phases: the only way into the application is 13 hand-authored CSVs. ~~Phase 11 — administrative surfaces~~ **done 2026-08-11**: FR-9 and FR-11 are `✓`, and the student has a screen. ⚠️ **Two small pieces of work are unscheduled.** **(a) FR-6's acceptance file** — Its criterion is SRS §6.7, quoted in `testing-strategy.md` §4; `DefaultRanker.rank()` implements both sentences and `GET /runs/{id}/candidates` returns that order; only the acceptance file is missing. **It is unscheduled — assigning it to a phase is the project owner's call.** **(b) The shortened-day shift in the timetable views** — ADR-003 gives the window one effect, *displayed and printed hours*; Phase 11 delivered the configuration and the administration screen's preview, and the timetable views and CSV export still print ordinary hours. FR-9's criterion is only about closing a half-day, so the tick stands; carrying the shift into the views is the project owner's call. Every other hold is outside the code: no supervisor-written acceptance standard (C-9 — FR-10, FR-18), a statement to reword (FR-8). ~~**Phase 10 — code.**~~ **Done 2026-08-10.** ⚠️ **C-15 had to be resolved first** — FR-4 is about the objective, and testing it before Phase 8 would have pinned the behaviour C-15 changed. ~~*(1) the timed FR-2 walkthrough*~~ — **run 2026-08-07, criterion reworded**, FR-2 `✓`. ~~*(2) a first live call to a language provider*~~ — **performed 2026-08-07**, `demonstration.md` §4, **FR-24 `✓`**; C-21 unchanged and the suite still calls no provider. **(3)** whether to open **increment 2** (Phases 13–14) remains the project owner's, and is not a prerequisite for Phase 10 |
| **Days used** | Phases 1–6 delivered against a budget of 3 + 5 + 3 + 4 + 2 + 3 = **20 of 20**, plus **Phase 7, which was budgeted none**. ⚠️ **That is C-1, and the ~2.5-day estimate it carried was itself understated** — ADR-010 itemises it as adapter + context builder + verifier + panel + report, all assistant work, with **regeneration costed nowhere**. Recorded rather than corrected: ADR-010 is a delivered commitment |
| **Repo** | https://github.com/JINZO-AI/optiedt-ai-timetabling · `main` · ⚠️ **neither the latest commit nor a commit count is recorded here.** Derive them: `git log -1 --oneline` · `git rev-parse --short origin/main` · `git rev-list --count origin/main..HEAD` (0 means everything is pushed), after a `git fetch`. This line named a SHA and was wrong **five** times; four were repaired by editing the value, which is exactly why there was a fifth. See [`docs/dashboard.md`](dashboard.md)'s Repository-status row |
| **Blocked on** | ✅ **Nothing, for the first time since 2026-07-29.** C-1 — *where the assistant and regeneration go* — was open for eight days and closed by Phase 7. What remains is **one** open question blocking requirement TICKS and nothing else: **C-9** blocks the `✓` of FR-6, FR-10 and FR-18, and it is **supervisor-dependent — it cannot be closed from this repository.** ⚠️ **NARROWED 2026-08-10 to FR-10 and FR-18.** Phase 10 sharpened what C-9 is; the pre-Phase-11 audit shrank it. **SRS Table 36 names a specifying section for three of C-9's original four**, and two of those sections state testable behaviour — **FR-6 → §6.7**, **FR-17 → §6.7 and §8.4 Table 34**. Both leave C-9; **FR-17 is `✓`** and FR-6 needs only an acceptance file. What remains is an acceptance *standard* for FR-10 and FR-18 — and for FR-18, **the definition of the occupancy figure itself**, which no document supplies and which **C-13 makes consequential**, so it is the one gap a session must not fill by choosing. ⚠️ **Nobody had checked Table 36 for five days**, because C-9 framed the gap as a missing §3.2 row. Read a requirement's Table 36 row before calling it unspecifiable. ⚠️ **This row said "two open questions" and named C-15 as blocking FR-13 until 2026-08-10; C-15 was resolved on 2026-08-07 and FR-13 has been `✓` since.** ⚠️ **C-9 blocks no software** — Phase 9 built FR-10 in full underneath it. Separately, ~~FR-24 waits on a live provider call~~ — **performed 2026-08-07 and FR-24 is `✓`** (`demonstration.md` §4) — and **FR-2 is `✓` since 2026-08-07**, criterion settled (reworded) and `acceptance/test_fr02` written, which is an act a person performs, not work a session can do |

---

## Blockers, precisely

*C-6, C-7, C-13, C-4, C-12, C-16, C-17, C-18 and now **C-5 and C-14** are all resolved and recorded in
`docs/open-questions.md`, which is the authority. What follows is only what is still open.*

**Phase 5 is closed and nothing blocked it. Phase 6 opened by settling the two that would have.**
C-5 and C-14 were decided by the project owner on 2026-08-05 and recorded before any code — C-5 by
clarifying the specification's wording and leaving `services/portfolio.py` alone, C-14 by adopting the
standard Pareto rule *and* moving the dominance signal off the top candidate, which are two independent
fixes for two independent defects. C-14 was the one that landed inside Phase 4 and was **deferred
rather than answered** on 2026-08-01: the comparison screen shipped with no dominance signal at all,
and M1 is what builds it.

### C-4 and C-12 — resolved 2026-07-30

**C-4.** All seven criteria (S2, S3, S4, S5, S6, S7, S10) now have a `v_i` and a `min_i`/`max_i`
formula, implemented in `analysis/criteria.py` and independently re-implemented as CP-SAT expressions
in `solver/objective.py` (the two layers may not share code — see that module's docstring). Full
formulas and the reasoning behind each choice, including the two genuine judgment calls (S4's resource,
S6's target), are in `docs/open-questions.md`.

**C-12.** S5 uses a labeled proxy — sessions placed in the first or last period of the day — rather
than real preference data, because the objectively better fix (a genuine preferred-window column) needs
`data/instance/` and `instance/loader.py` changes that were outside this session's scope. The proxy
gives S5 genuine candidate-dependent variation (confirmed on the real reference instance: 91–116 of 218
sessions touch an edge period, depending on the profile), which is what the C-12×C-5 risk needed —
without resolving C-5 itself.

**Owed and closed alongside C-4:** the objective's auxiliary variable count, **measured at 5,249** under
catalogue weights and **0** when every weight is zero. `solver/objective.py` builds
`occ`/`any`/`first`/`last`/`idle` variables per (teacher-or-leaf-group, day) pair and per-room deviation
variables for S6; the per-criterion breakdown is in Measurements below and in
`docs/constraint-model.md`, which no longer carries an order-of-magnitude estimate. Closes the last open
half of C-7.

### C-16 — resolved 2026-07-30

**Reproducibility and "at least three candidates" both hold**, at production settings, via
`interleave_search = true` and withholding the warm start when an objective is posted. ADR-011 was
amended rather than reversed: deterministic time bounds the *work*, `interleave_search` orders the
*race between workers*, and both are needed. Full account in `docs/open-questions.md`, including the
reasoning error that made this look like a specification conflict for one session.

### C-17 — resolved 2026-08-04

Enforcement literals defeat CP-SAT's presolve: an infeasibility a plain solve proves in **0.0 s**
returned `UNKNOWN` after **240 s** under assumptions, on both realistic infeasible variants of the
reference instance. Stage 3 now withdraws one rule at a time and solves plainly, so presolve keeps working. The
same instance is answered **`('H3',)`, minimal, in 1.9 s**. `docs/architecture.md` stage 3 is rewritten,
and two of its three "imposed" properties changed — they were imposed by the assumption mechanism, not
by CP-SAT. **Blocks nothing.**

### C-5 and C-14 — resolved 2026-08-05 by project-owner decision

**C-5 → clarify the wording, keep the implementation.** Duplicate removal stays exactly as SRS Table 29
specifies. The acceptance criterion is tied to **the verified reference instance at production
settings** — three *distinct* candidates — while the general contract the software makes on any
instance is "at most three, duplicates removed". The test asserts **exactly three**, not "at least
two": the measurement is 3 distinct / 0 removed, and a weaker assertion would hide a regression rather
than describe the product. ⚠️ It is therefore an explicitly instance-specific criterion, and C-16
records the same instance returning **one** candidate at a single worker — the failure mode is real and
the test is what would catch it.

**C-14 → the standard Pareto rule, and the signal moves off the top candidate.** Two independent
defects, and the decisive fact is that they are independent: switching to Pareto does **not** make the
"dominated top candidate" clause reachable, because `TIE_BREAK_ORDER` covers all seven criteria so a
dominated candidate still cannot rank first. So the reading changed *and* the signal moved to any
candidate in the portfolio. `Recommendation.dominated_by` remains provably `None` and is kept dead
visibly.

### Still open, blocking something later

✅ **C-15 — RESOLVED 2026-08-07, and the resolution refuted its own diagnosis.** It read *"the objective
weights raw counts of incomparable scale"* and blocked FR-13. Six measurements on the reference instance
killed four candidate fixes: normalising the objective by bound range is **worse** (S3 has the largest
range of the seven, so dividing by it shrinks S3 most — raw S3:S5 = 1:1.33, normalised 1:4.6);
renormalising the weights returned a **bit-identical** timetable (scaling cannot move an argmin);
tripling the budget left a ~16-unit gap; and the objective terms are correct (**S3 alone reaches 0,
proven optimal, in 14.45 of 90 budget units**).

**The objective formulation is sound and is unchanged.** What was wrong was *which criteria the profile
raised*: S5 is an admitted proxy for absent preference data (C-12) and the most expensive criterion to
optimise, so weighting it 0.40 left teacher-favouring **worst of the three on S3, S4 and S5 at once**.
`teacher-favouring` now raises **S3 and S4**. Measured: S3 **29 → 0**, S5 103 → 95, score 79.45 → 81.10.
**FR-13 is `✓`.**

**C-9 — originally four requirements, NARROWED on 2026-08-10 to two: FR-10 and FR-18.** ⚠️ **It does not block the Phase 6
acceptance suite**, and the claim that it did was corrected on 2026-08-05 by checking it rather than
repeating it: neither the nine acceptance criteria below nor `testing-strategy.md` §4's table names
FR-6, FR-10, FR-17 or FR-18. The four requirements without a specification are also the four with no
acceptance test to write. What it blocks is the `✓` of FR-6, FR-10 and FR-18 — a requirement cannot be
verified against a criterion nobody wrote. FR-17's criterion now comes from C-14's reworded
`scoring-and-explanation.md` §Dominance, which is this project's own design document rather than the
SRS row that is still missing.


---

## Next, in order

✅ **All ten entries below are struck through and done.** Item 9 — H10's dormant gap — was the last,
closed on 2026-08-06 by Phase 7 M1 once C-19 decided how a locked session's target reaches the solver.

**The completed entries are kept rather than deleted**, and deliberately: several carry a correction
that other documents cite by number. Item 3 records a blocker that was never real ("a plausible
blocker nobody tried to falsify"), item 4 records the ~11× overshoot that turned out to be an
aggregate misread, and item 10 records what the generator does and does not reproduce. Deleting them
would break those references and lose the reasoning that makes each correction checkable.

**So: read item 9, and read the others only if you are following a cross-reference to one.**

1. ~~Loader~~ · ~~Model H1–H12, H12 bug fixed~~ · ~~Decide C-13~~ · ~~Decide C-7~~ — **all done**, see
   `docs/history.md`. Phase 2 is closed.
2. ~~Decide C-12 and C-4~~ · ~~Implement the seven criteria, scoring, ranking, the objective, the
   recommendation translator, the four properties~~ — **done 2026-07-30**. See `docs/dashboard.md`'s
   "Phase 3 — what was built" for the precise file list and what each one does and does not cover.
3. ~~**Portfolio orchestration**: loop over the 3 profiles, score each candidate, remove duplicates.~~
   **Done 2026-07-30** — `services/portfolio.py`, 16 unit tests. On the reference instance: 3 distinct
   candidates, 0 duplicates.
   ⚠️ **This entry previously claimed it was blocked on C-5 and belonged to Phase 4–5. Both were
   wrong.** `docs/open-questions.md` is the authority on what an open question blocks and records C-5
   against *Phase 6 acceptance*; SRS Table 29 already fixes the implementation behaviour ("at most 3,
   duplicates removed"), so only the acceptance *wording* was ever undecided. And `services` needs no
   database to run a portfolio — "needs `services`" is not "needs Phase 4". The error cost nothing here
   because it was caught, but it is the same shape as C-13: a plausible blocker nobody tried to falsify.
4. ~~**Recalibrate the deterministic-time budget.**~~ **Done 2026-07-30.** The budget was never
   failing: it binds exactly per worker, and the "~11× over-run" was `deterministic_time` reporting the
   sum across workers. Calibration in Measurements below; correction in C-2. What the calibration
   *did* uncover is **C-16**, resolved the same day — `interleave_search` makes the parallel search
   deterministic, so ADR-011 was amended rather than refuted.
5. ~~**Validation on the published ITC-2007 instances.**~~ **Done 2026-07-31**, closing Phase 3.
   `optiedt.validation.itc2007` reads the `.ctt` format (**not `.ectt`** — an earlier note in this file
   named the wrong extension; the archive holds plain `.ctt`), implements ITC-2007's own four hard
   constraints and four soft costs, and models the problem in CP-SAT. Run it with
   `scripts/validate-itc2007.ps1`. Results in Measurements below.

**Phases 3 and 4 are closed.** What follows belongs to Phases 5–6, in this order:

6. ~~**Phase 4 — the web interface.**~~ **Done 2026-08-01**, six milestones. The availability grid,
   generation screen, comparison screen and four timetable views all exist, and the portfolio and the
   decomposition are now reachable by a user. **C-14 was deferred, not settled** — the comparison
   screen ships no dominance signal, because the indicator both documents ask for can never fire.
   ⚠️ **One thing is owed:** the FR-2 acceptance criterion ("filled in under 5 minutes without
   training") is about a person and needs a timed walkthrough. Carried to Phase 6.
7. ~~**Port the five verifications into the application** as FR-12.~~ **Done 2026-08-03**, Phase 5 M1.
   `optiedt/preanalysis/verifications.py`, wired into the run's `PREANALYSIS` state, returned by
   `GET /runs/{id}` and displayed on the generation screen. **Both bounds are ported**, and
   `tests/unit/test_preanalysis.py::test_the_original_room_mix_is_caught` reconstructs the pre-repair
   room mix and requires the contiguity bound to name both shortfalls — the period bound passes that
   instance at 95.2 %. The two implementations are compared numerically by
   `tests/integration/test_preanalysis_matches_verifier.py` rather than trusted to agree.
   ⚠️ One half of verification 5 is deliberately **not** ported: `Instance` excludes `Student`
   (increment 2), so "425 students match the declared sizes" stays with `verify-instance.ps1`. The
   in-application check says so in its own report rather than passing for the documented one.
8. ~~**Phase 5.**~~ **Done 2026-08-04**, six milestones: FR-12 in-app with both bounds, FR-8's diagnosis
   (C-17 replaced the documented mechanism on measurement), FR-19's run record in PostgreSQL, FR-11's
   authentication and rights (C-18 decided how accounts are provisioned), publication with its trace,
   and a closing audit that found eight defects.
9. ~~**Fill H10's dormant gap** when recommendation regeneration needs it: `build_variables` refuses
   to run if any session is locked, because `SolverInput` carries session ids without the target slot
   and room.~~ **Done 2026-08-06**, Phase 7 M1, under **C-19**. `SolverInput.locked_sessions:
   frozenset[SessionId]` was **replaced** by `locked_placements: frozenset[Placement]` — the domain's
   own `Placement`, because a lock *is* a placement the solver must reproduce. H10 is now applied by
   domain pruning like the other five domain-pruned rules, so it carries no assumption literal (C-6)
   and costs nothing during search.

   ⚠️ **A lock INTERSECTS the other rules' pruning; it never replaces it.** A lock naming a closed
   slot, a slot the teacher declared unavailable, or a room too small for the group raises naming the
   session, the target and the rule that refused. Had it replaced the pruning, an accepted
   recommendation could have placed a session where a hard rule forbids — an invariant-2 violation
   arriving through the one door recommendations are allowed to use.

   ⚠️ **Locking a session of a cumulative room type takes that whole type out of the cumulative
   encoding, and that is required rather than tolerated.** A cumulative-encoded session has no
   `assign[s, r]` variable and its room is chosen by a post-solve labeller (`solver/engine.py`), which
   cannot honour a lock. Narrowing `candidate_rooms` makes the type stop being fully interchangeable,
   so H7's exactly-one posts over a single room and the lock binds.
   `test_locking_a_cumulative_type_falls_back_to_the_per_room_encoding` fails if that ever stops
   happening — which would leave H10 unenforceable for a room type while still appearing to be applied.

   **Verified against the real solver, not only against the domains** (`tests/integration/test_h10_locks.py`,
   4 solver-marked tests): the limiting case locks **all 218 placements** and the solver returns exactly
   the timetable it was given.
10. ~~**Write the instance generator** (`data/generator/`), a stated deliverable of PPM §10.~~
   **Done 2026-08-05**, Phase 6 M5. `data/generator/generate_instance.py` — standard library only,
   importing nothing from `backend/`, because the 13 CSVs *are* the contract between generator and
   application and neither side may depend on the other.

   **Its output passes `data/verification/verify_instance.py` on every figure**, including the two
   derived ones that are not simple counts: **heaviest load 12 periods (18 h)** and **smallest margin
   11 free slots**. Both occupancy bounds land exactly — Lab_Info 90.9 % of two-period windows against
   71.4 % of periods. The verifier gained an `--instance` flag so the generator can be held to the same
   contract as the committed files without overwriting them.

   ⚠️ **And the generated instance SOLVES: 218 of 218 sessions placed in 5.1 s.**
   `verify_instance.py` passing is *necessary and not sufficient* — that is the whole of C-13 — so
   solvability was measured rather than assumed.

   ⚠️ **It reproduces the documented FIGURES, not the committed rows, and that is a deliberate limit
   rather than an approximation.** `data/instance/` carries 425 student names, 44 teacher names and one
   particular teacher-to-session assignment drawn from a random stream nobody committed. That stream is
   not recoverable, so a generator emitting those exact rows would be a copy wearing a generator's name.
   What ADR-008 actually binds is that the documents state the instance's content and its five
   verification results **as facts** — and those are what survive. The generator **refuses to write into
   `data/instance/`**, because replacing it would invalidate every measurement in `docs/` — scores,
   timings, the S5 range, the occupancy figures on screen — without one of them failing.

   ⚠️ **Added to this list 2026-07-31.** It had been recorded in three places — `data-and-instance.md`,
   ADR-008, and C-11's body — and scheduled in none, which is how a deliverable inside a section headed
   *RESOLVED* goes missing.

Persistence can wait until Phase 5: the solver reads the CSVs through the loader, and PostgreSQL is
only needed once runs, candidates and publication have to survive a restart.

### Recorded from the 2026-08-07 first-use session — ⚠️ NOT SCHEDULED

**These are findings, not commitments.** They came from the FR-2 walkthrough
([`docs/demonstration.md`](demonstration.md) §2), where the grid passed and **the product around it did
not**. They are written down so the feedback is not lost, and left unscheduled because **where remaining
work goes is the project owner's call, never a session's** — no phase or increment carries them.

| # | Finding, in the words it was reported in | Nearest existing requirement |
|---|---|---|
| U1 | *"Navigation is confusing"* — the person in charge lands on `Disponibilités`, a teacher's data-entry screen. There is no home | none — UX |
| U2 | *"Users do not understand the purpose of each action"* — the generation screen offers only `Graine` and `Budget déterministe (pas des secondes)`, two raw solver parameters | none — UX |
| U3 | *"Some pages lack clear explanation"* — no empty-state guidance, no inline help | none — UX |
| U4 | A **registration flow was looked for and does not exist**. That is C-18 working as designed (accounts come from the seed), but the expectation is real and the sign-in screen is the only thing that says so | C-18 |
| ~~U5~~ | ~~Export / print of a timetable was expected~~ — ✅ **ADDRESSED 2026-08-10 by Phase 9.** Both halves exist on all four views: a print button producing an identified sheet, and a CSV download carrying the run's trace | **FR-10**, now `WIP` — software done, tick held by **C-9** |
| U6 | An English interface with a French option was expected | none — the specification and instance are French (`CLAUDE.md`, Conventions) |

⚠️ **U6 conflicts with a recorded convention and is not a defect.** French domain vocabulary is kept
verbatim on purpose — `CM`/`TD`/`TP`, `Amphi`, `Maitre de Conferences` — because it matches the instance
CSVs, and translating it "creates a mapping layer between the application and its own data for no
benefit." Any English interface keeps those terms. Recorded as a product decision to take, not as work
to schedule.

⚠️ **U5 was the only one of the six that is already a requirement, and it is the only one that has been
acted on.** The rest would be new scope and remain unscheduled — U1, U2 and U3 are usability findings
with no requirement behind them, U4 is C-18 working as designed, and U6 conflicts with a recorded
convention (below). **Phase 9 closed U5 because FR-10 exists, not because a first-use session asked for
it**; that distinction is what keeps this table findings rather than a backlog.

## Phases — increment 1: 20 budgeted working days, plus one unbudgeted phase

⚠️ **This heading read `Phases — increment 1, 20 working days` until 2026-08-06, and it was half of a
contradiction the repository carried for eight days.** It equated the plan's six phases with the
increment; ADR-010 commits FR-22, FR-23 and FR-24 to increment 1 and the six phases name none of them.
Both statements were here and they could not both be right (**C-1**). **The heading moved, and ADR-010
did not** — it is a delivered commitment. Phase 7 is what makes the two consistent, and its days are
marked unbudgeted because that is what they were.

| Phase | Work | Days | Milestone |
|---|---|---|---|
| 1 | Needs, specification, source evaluation, instance verification | 3 | Instance verified, sources evaluated, scope fixed |
| 2 | Modelling H1–H12, first valid timetable | **5** | A timetable without conflict on the instance |
| 3 | Profiles, portfolio, score, ranking, decomposition, recommendation catalogue, regeneration, validation on published instances | 3 | Several candidates produced, ordered, and a difference decomposed |
| 4 | Availability grid, generation screen, comparison screen, views | 4 | Complete path from declaring availability to publication |
| 5 | Pre-solve verification, diagnosis run, authentication, rights, run record | 2 | An infeasible instance produces a report naming the rules in conflict |
| 6 | Tests, documentation, presentation | 3 | Application demonstrable, documents complete |
| **7** | **Regeneration (FR-23) and the assistant (FR-22, FR-24, FR-25)** | **0 — unbudgeted (C-1)** | **Increment 1 complete: a recommendation regenerates through the same solver, and the assistant explains under a grounding check** |

Phase 2 gets the largest share because it carries the most uncertainty.

**Increment 2, conditional on remaining time:** examination session (4 d), weight adjustment (3 d).
Natural-language constraint entry is **not undertaken** — it would require a solver-validation harness
that does not fit the project (see `docs/ai-integration.md`).

---

## Order of scope reduction, if the work runs late

Decided in advance, so the decision is not taken under pressure:

✅ **None of it was used.** Phase 7 delivered the report along with everything else, so step 1 — the
first and only cut that increment 1 ever came close to — was never taken. The order stands unchanged
for increment 2.

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
| ~~**~2.5 unbudgeted assistant days** (C-1)~~ | ~~≈12% overrun on 20 days~~ | **REALISED and CLOSED 2026-08-06.** Phase 7 was approved and delivered all four requirements; the release valve was never used. ⚠️ **The estimate was itself understated**: ADR-010 itemises it as adapter + context builder + verifier + panel + report — all assistant work, with **FR-23 costed nowhere** — so the true overrun was larger than the figure four documents repeated. Recorded rather than corrected inside ADR-010, which is a delivered commitment |
| ⚠️ **No test can establish that a real provider works** (C-21) | **Permanent, and unchanged by FR-24's `✓`**: a green build is still not evidence about a language model | **Deliberate, not a gap.** A model's output is not fixed by a seed, so such a test would report the machine and the day. What is verified is the application's behaviour *around* a provider — the context it sends, the check it applies, what it displays when the check fails. **The first live call was performed 2026-08-07** and is recorded in `docs/demonstration.md` §4; it is a dated record, not automation, and it is what FR-24's `✓` rests on. ⚠️ It also exposed a defect the suite could not: the adapter sent no `User-Agent` and a CDN refused it, so every answer silently fell back — **correct degraded behaviour concealing a broken integration** |
| **91% laboratory occupancy** (of two-period windows) | A modelling regression looks like an infeasible instance — **and, as C-13 showed, an infeasible instance looks like a slow model** | Pre-analysis first, always, and read the *window* figure rather than the period figure. Re-check both whenever the instance changes |
| **A pre-analysis check that is necessary but not sufficient** | Passes an infeasible instance, so the next failure is attributed to the model. Cost three sessions on C-13 | Both bounds now checked in `verify_instance.py`. Any new check must state whether it is sufficient, and FR-12 must port both |
| **The cumulative reformulation and the warm-start were built for a problem that did not exist** | Two committed mechanisms (`cumulative_room_types`, `solver/warm_start.py`) are carried for a reason now known to be wrong. Both are correct and tested, neither is load-bearing: the model solves with the warm start off, and the greedy now reaches 218/218 in 0.04 s | **Still not removed.** The objective has now landed and confirmed a real cost: `cumulative_room_types` also means S6 (room efficiency) cannot be optimised for those room types at all, only scored after the fact — see below. **Whether the plain per-room encoding would now serve for every type remains untested** |
| **Objective encoding — done, with one gap** | S2–S5, S7, S10 are fully encoded in `solver/objective.py`. **S6 only covers non-cumulative room types (Salle)** — cumulative types (Amphi, Lab_Info, Lab_Sciences) have no per-room CP-SAT variable, only a post-solve labeller the objective cannot influence | `analysis/criteria.py` still scores S6 correctly for every room. Closing the solver-side gap needs `solver/variables.py` changes (out of the scope this landed in) |
| ~~**Deterministic-time calibration — the budget does not bind**~~ | ~~a consistent ~11× over-run~~ | **RESOLVED 2026-07-30 — the claim was false.** The budget binds exactly, per worker; `deterministic_time` reports the sum across workers, and ~11 was the worker count. Calibration recorded in Measurements below. See C-2 |
| ~~**Reproducibility does not hold at the production worker count**~~ | ~~identical runs returned different candidates~~ | **RESOLVED 2026-07-30 (C-16).** `interleave_search = true` makes the search deterministic at full parallelism; the warm start is withheld under an objective because it pinned all three profiles to one timetable. Both criteria now met simultaneously, and the configuration is ~2× faster than before. ADR-011 amended |
| ⚠️ **`interleave_search` is marked "Experimental" upstream** | Reproducibility — a written acceptance criterion — now rests on one OR-Tools parameter whose guarantee could change between releases | **Pin the OR-Tools version.** `tests/integration/test_reproducibility.py` verifies the behaviour at production settings rather than trusting the documentation; treat a failure there as blocking, not flaky |
| ⚠️ **`interleave_search` misreports `CpSolver.objective_value`** | Measured 2026-07-31 on ITC-2007 comp02/comp18/comp21: the reported objective sat **5–15 units above** the objective expression evaluated at the solution the solver returned, on solves that stopped before proving optimality. With the parameter off, the two agree exactly | **Affects nothing today, by design.** No score, ranking, comparison or display reads `SolverOutput.cost` — `analysis/criteria.py` recomputes every criterion from the placements, which the ban on `analysis → solver` forces. The two guards that could have gone flaky were pinned: `test_objective_matches_analysis.py` requires `proven_optimal`, and the ITC-2007 harness compares the encoding rather than the reported objective. **Do not start ranking on `cost`** — ADR-011 |
| ~~**Raw-weight objective lets a large-scale criterion swamp a small one**~~ | ~~"Teacher-favouring" does not favour teachers on S3~~ | **RESOLVED 2026-08-07 (C-15) — and the diagnosis in this row was wrong.** The raw-weight formulation is sound and is **unchanged**; both proposed fixes named here were measured and refuted. Normalising by bound range is **worse** — S3's range (752) is the largest of the seven, so raw S3:S5 = 1:1.33 becomes 1:4.6. Per-criterion emphasis was not needed. The real fault was *which criteria the profile raised*: S5 is an admitted proxy (C-12) and the most expensive criterion to optimise, and head-to-head at production settings teacher-favouring came back **worst of the three on S3, S4 and S5 at once**. It now raises **S3 and S4**; S3 **29 → 0**, S5 103 → 95, score 79.45 → 81.10 |
| **Candidates are not shown as they are produced** | `docs/architecture.md` stage 2 and ADR-005 both list incremental visibility as a benefit. `services/portfolio.py` returns the whole `PortfolioReport` at the end, so the generation screen shows `SOLVING` for the full 105–150 s and every candidate arrives at once | **Found by the Phase 4 closing audit, 2026-08-01.** Nothing is incorrect — the candidates are right and the states honest — but a stated benefit is unrealised. Both documents now say so. Closing it means `generate_portfolio` publishing each candidate through a callback or the store instead of its return value, which changes a **Phase 3** module's contract. Not attempted during Phase 4 |
| ~~**Both stores are in memory**~~ | ~~a restart loses every run~~ | **RESOLVED 2026-08-04, Phase 5 M3 (FR-19).** PostgreSQL 17 behind the same Protocols, and **no router changed** - which is what those Protocols were for. Verified by killing the API and reading a run back from a fresh process. `persistence = memory` stays available for tests and for a demonstration without a database, and is **configuration, never detection**: a store that fell back to memory when the database was unreachable would lose every run while the application looked healthy |
| ~~**No authentication**~~ | ~~every endpoint is open~~ | **RESOLVED 2026-08-04, M4.** Bearer tokens, RBAC per endpoint, and the teacher taken from the token rather than a dropdown. ⚠️ **Still must not be exposed**: `secret_key` defaults to `change-me-in-env`, published in this repository, so a deployment that does not set `OPTIEDT_SECRET_KEY` signs tokens anyone can forge |
| **7 `npm audit` advisories in the frontend toolchain** | 1 critical, 1 high, 5 moderate as of 2026-08-01: `vite`/`esbuild` (dev-server request forwarding), `react-router`, and the `vitest` chain that depends on `vite` | **All are dev dependencies**, and `vite 5.4.21` / `react-router-dom 6.30.4` were already pinned before `vitest` was added, so most pre-date it. Not force-upgraded during Phase 4: `npm audit fix --force` means breaking changes to `vite` and `react-router` mid-phase. ⚠️ **Recorded here 2026-08-01 because it existed only in a commit message** — a Phase 4 verification found nothing in `docs/` about it. Address deliberately, and re-run `npm audit` before believing this row |
| **Exam multi-room assignment** (R-6) | Breaks a shared `room[s]` abstraction | Keep it out of shared solver code from the start |
| ~~`uv` not installed~~ | — | **Resolved.** uv 0.12.0 installed; the whole toolchain runs |
| **Kaggle `students.csv` holds personal data** | 3,000 rows with names, emails, phones, addresses | Never load it beyond `student_id` + enrolment; never let such a field reach the assistant context |
| ~~**`recommendations/translator.py` cannot build a complete `SolverInput`**~~ | ~~`Run` carries no instance reference or base profile weights~~ | **RESOLVED 2026-08-06, Phase 7 M2 (C-20).** `services/regeneration.py` is the layer the docstring had been pointing at since Phase 3: it merges the `RunOverride` with the origin run's weights, seed and budget. `translator.py` is unchanged and still returns plain domain data, and the new **`recommendations ⇸ solver`** contract keeps it that way. ⚠️ **One limit is carried forward and written down rather than assumed**: `Run` still holds no instance reference, so a regeneration reloads the single instance this deployment serves. The day a second exists, `Run` must gain the reference — C-20 clause (ii) |
| ~~**C-12 × C-5 interaction**~~ | ~~If S5 measures zero, the teacher-favouring profile differs by S3 alone, candidates converge, and the "three candidates" acceptance test fails for an invisible reason~~ | **C-12 resolved 2026-07-30** — S5 now varies genuinely with the candidate (measured 91–116 of 218 sessions on the reference instance across two profiles). **C-5 itself is still open** and still needs its own decision before the FR-13 acceptance test is written |

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
| **FR-24 — the first live provider call** | **3 of 3 answers generated, 0 discarded, figures matching the screen** | 2026-08-07 | Groq · `llama-3.3-70b-versatile`, against a real run at production settings (seed 42, budget 90, 3 distinct candidates, top score **80.30714644396436**). The explanation quoted the normalised values exactly — `0.9773936170212766` (S3), `0.6453488372093024` (S4), `0.8539144471347861` (S6); a question the context could answer returned the top score to three decimals; a question it could **not** answer was declined with no invented figure, which is FR-24's criterion. Full record and the one imprecision found in the answer: `docs/demonstration.md` §4. ⚠️ **Not a test and never will be (C-21)** — one call, one day, one model. ⚠️ **It exposed a real defect the suite could not see**: the adapter sent no `User-Agent`, so a CDN refused it (HTTP 403 / Cloudflare 1010) and every answer fell back to its computed form — degraded mode working correctly *while the integration was broken*, which is why four closing audits missed it |
| **Instance generator** | **13 files, every documented figure, and the result SOLVES** | 2026-08-05 | Phase 6 M5. `data/generator/generate_instance.py` output passes `verify_instance.py` on all 25 checks including the two derived ones - heaviest load 12 periods (18 h), smallest margin 11 free slots - and both occupancy bounds land exactly (Lab_Info 90.9 % of two-period windows, 71.4 % of periods). ⚠️ **Solvability measured, not assumed: 218/218 placed in 5.1 s** at a deterministic budget of 30. A passing verifier is necessary and not sufficient - C-13 - so the check that matters most is the one no arithmetic can make |
| **Acceptance suite, after Phase 9** | **112 tests, 15 requirements, all passing.** Wall clock **16 min 23 s idle, 21 min 38 s under concurrent load, 18 min 27 s on 2026-08-10 and 18 min 30 s when the closing audit re-ran it the same day** — ⚠️ **a range, not a figure**: ADR-011's rule that wall-clock cost varies by machine applies to this row too, and the second measurement is the same machine with one other process running. Quote the range or quote neither. ⚠️ **This row said "106 tests, 14 requirements" until 2026-08-10** — stale by Phase 8's `test_fr02`, not by Phase 9, which added no backend test | 2026-08-06 · re-measured 2026-08-07 and 2026-08-10 | Phase 7 M2–M5 added FR-22, FR-23, FR-24 and FR-25 to the ten Phase 6 covered; Phase 8 added FR-2. **Phase 9 added none** — FR-10 has no criterion to write one against (C-9). **71 need no solver and run in `run-checks.ps1`**; the **36** that solve for real drive **four** production portfolios (seed 42, budget 90) — one shared by FR-3/FR-13/FR-19, a second for FR-19's repeat, and **two more for FR-23**, because "regenerate from this run" is a question one run cannot answer, exactly like "repeat this run". ⚠️ **The three assistant requirements add no solve at all**: their criteria are about the service being off, which is the default configuration |
| **Acceptance suite** | **64 tests, 10 requirements, all passing** | 2026-08-05 | Phase 6 M2-M4. FR-3, FR-5, FR-8, FR-9, FR-11, FR-12, FR-13, FR-15, FR-17, FR-19, driven through the HTTP API. 33 need no solver and run in `run-checks.ps1`; the 26 solver-marked ones run in about **8 min** on **two** production portfolios (seed 42, deterministic budget 90), shared across FR-3, FR-13 and FR-19's first run. ⚠️ **A budget of 9 does not work and is not a smaller version of 90**: the portfolio divides the total between three profiles, each solve carries the objective, and 3 per profile returns `UNKNOWN` — the run lands in `FAILED` rather than presenting a non-answer. The 2.8–3.3 s row below is a *feasibility* solve with every weight at zero |
| **A figure read two ways on one page** | **`1.9183673469387754` beside `1.92`** | 2026-08-06 | Phase 7 M4, found by opening the running application rather than by a test. The comparison table rendered S6's raw value as `1.92`; the assistant's computed form two panels below printed the full float. Neither was wrong and the page still looked like two parts of one application disagreeing about a number — the same failure mode as the contributions-rounding defect Phase 4 M5 found, and the same fix: **one rule for a figure, applied wherever it appears** |
| **The grounding check had a hole, and a test found it** | **`4271` matched nothing at all** | 2026-08-06 | Phase 7 M3. The number pattern was `\d{1,3}(?:[ ]\d{3})*` — up to three digits, then optional space-grouped triples. On `4271` it matched `427`, the trailing word boundary failed on the `1`, every shorter attempt failed the same way, and every later start was refused by the leading boundary. **A verifier that cannot SEE a number cannot reject it**, so any ungrouped number above 999 passed as grounded — precisely the range an invented count of minutes, periods or sessions falls in. Found by `tests/acceptance/test_fr22.py`, which fabricated exactly such a figure; **not by review**, and the module had been read twice |
| **FR-23 regeneration** | **a new run, and the locked session comes back where it was locked** | 2026-08-06 | Phase 7 M2. `tests/acceptance/test_fr23.py`, **14 tests**; the four solver-marked ones run **two production portfolios in 7 min 52 s** (seed 42, budget 90). Measured on the regenerated run: `COMPLETED`, **218/218 placed in every candidate**, the locked session at exactly the slot and room it held in the origin candidate, and **H1, H3, H8 and H9 re-derived from the placements** rather than taken from CP-SAT's status. ⚠️ The origin run is byte-identical before and after — invariant 6, asserted rather than assumed |
| **Toolchain** | **all green** | 2026-08-06 · re-measured **2026-08-10** | **11/11** layer contracts kept · ruff · format · mypy strict on **78** source files · **517 backend tests** (411 fast + 62 solver-marked + 44 database-marked) · instance verified · frontend `tsc` clean · **81 frontend tests** (`vitest`). ⚠️ **This row read "510 backend (404 fast) · 53 frontend" until the Phase 9 closing audit on 2026-08-10.** It was stale twice over — by Phase 8's `test_fr02` and `test_config_guard`, and by Phase 9's 28 frontend tests — and **Phase 9's own documentation pass corrected the dashboard's two copies of these figures and missed this third one.** That is the recurring fault of this project in miniature: a figure stored in more places than anyone remembers to check. **Derive it** — `uv run pytest --collect-only -q` and `npm run test`. `run-checks.ps1` has **nine** steps: the database step FAILS **when no database was reached**, and SKIPS when Docker is absent. ⚠️ **The failing half was broken until Phase 6 M1** — it tested the Docker daemon, not the outcome, so a stopped container let all 38 tests skip and the step print `[ok]`. Found by reading the step's output rather than its tick; fixed to require tests that actually passed, and the guard verified to fire by stopping the container. Phase 5 M1 added 32 backend and 5 frontend; M2 added 13 backend and 6 frontend; M3 added 30 backend. Ninth contract (`api ⇸ solver`) added in Phase 4 M1 and verified to fire; `pytest` exit 5 no longer tolerated |
| **FR-12 in the application** | **the five checks reproduce `verify-instance` exactly** | 2026-08-03 | Phase 5 M1. Rendered on the generation screen during a real run: Amphi 32/56 = 57.1 % · Lab_Info 160/224 = 71.4 % **and 80/88 two-period windows = 90.9 %** · Lab_Sciences 48/84 = 57.1 % and 24/33 = 72.7 % · Salle 82/196 = 41.8 %; heaviest load 12 periods (18 h); smallest margin 11 free slots. Two independent implementations agreeing is what makes the figures trustworthy rather than merely self-consistent |
| **The report survives a failed run** | **verified** | 2026-08-03 | Budget 3 makes CP-SAT return `UNKNOWN` and the run lands in `FAILED` — and the pre-analysis report is still displayed. That is the C-13 case: when the solver cannot prove an infeasibility, the report is the only thing that says whether the instance is structurally sound |
| **Python** | **3.14.2** | 2026-07-29 | Resolved by uv 0.12.0 |
| **OR-Tools CP-SAT imports and solves** | **yes** | 2026-07-29 | On Python 3.14. `max_deterministic_time` **is accepted by the solver parameters** — ADR-011 is implementable, not just plausible |
| **Deterministic time → wall clock, reference instance** | **1 deterministic unit per worker ≈ 4.8 s wall at `workers=1`; ≈ 19 s at `workers=0` (16 cores)** | 2026-07-30 | ✅ **ADR-011's overdue Phase 2 calibration, discharged.** Budget 5, objective posted, catalogue weights. `workers=1` → 24.1 s · `2` → 17.2 s · `4` → 17.5 s · `8` → 57.2 s · `0` → 94.8 s. More workers cost *more* wall clock for the same per-worker budget, because the budget is per worker and the total work scales with the count |
| **Does `max_deterministic_time` bind?** | **Yes — exactly, per worker** | 2026-07-30 | ⚠️ **This corrects a recorded error.** Budget 5 → reported 5.00 at `workers=1` (ratio **1.00**); 8.79 at 2, 13.70 at 4, 30.26 at 8, 53.63 at 0. `CpSolver.deterministic_time` reports the **sum across workers**, so the "~11× overshoot" previously recorded here was an aggregate misread as an overrun. A whole portfolio at total budget 15 consumed exactly 15.0 at one worker. The budget was never failing |
| ~~Deterministic time → wall clock (superseded)~~ | ~~"not a clean ratio"~~ | ~~2026-07-30~~ | **Superseded by the two rows above.** The original observation — 60 requested, 247.98 consumed — was the same aggregate artefact, measured on an infeasible model. Kept so the correction is traceable |
| **First valid timetable** | **2.84–3.30 s wall · 0.13–0.21 deterministic** | 2026-07-30 | ✅ **Target < 60 s met with a wide margin.** Seven seeds (1, 7, 42, 123, 999, 2026, 31337), production defaults (`num_workers=0`, warm start on); all seven placed 218/218. Full pipeline: warm-start construction, solve, and independent re-verification of every hard constraint from the raw CSVs (`tests/integration/test_h1_h12.py`). Measured on the repaired instance — see C-13; the earlier `UNKNOWN` results were an infeasible instance, not a slow model |
| **Portfolio of 3 candidates** | **147–150 s (2.5 min) at production settings** — 3 distinct candidates, 0 duplicates, reproducible. ✅ **Target < 5 min met.** (Before C-16: 306 s, not reproducible) ⚠️ **The budget this was measured at is NOT established — see the note.** | 2026-07-30 | Reference instance, seed 42, three profiles. ⚠️ **This row contradicted itself until 2026-08-01 and the contradiction is not resolvable from the repository.** It said "total budget 90" *and* "budget divided 5 per profile" — but `services/portfolio.py` divides the total between the profiles, so 5 per profile means a total of **15**, not 90. Both readings are attested: `docs/open-questions.md` names 90 among the budgets tested, and its superseded C-16 table records the 306 s "before" figure at total budget **15**, while the C-16 before/after table names no budget at all. **Neither figure is quoted here now, because picking one would invent a measurement.** Re-measure before citing a budget with these timings. The *timings* themselves are unaffected and were reproduced. ⚠️ Separately: **the 5-minute figure is an estimate, not an acceptance criterion** — ADR-011 demoted both the 60 s and 5 min figures to "estimates, not wall-clock promises". Do not turn it into a promise: a deterministic budget is a unit of *work* and its wall-clock cost varies by machine |
| **Portfolio reproducibility** | **✅ at production settings** | 2026-07-30 | With `interleave_search = true` and the warm start withheld under an objective: two identical runs agree on candidate ids, order, placements, scores and sub-scores. **Before** the change, `workers=0` gave different order and different scores on every repeat; `workers=1` reproduced but yielded only 1–2 candidates. See **C-16** |
| **Effect of the C-16 configuration** | wall **306 s → 147–150 s**; candidates 3 → 3; reproducible **no → yes**; best score 82.23 → 80.31 | 2026-07-30 | Reference instance, seed 42, total budget 90. Roughly 2× faster and reproducible, at ~1.9 score points — the luck of a racing parallel search, given up deliberately. H1–H12 re-derived from the raw CSVs for all three candidates and the feasibility path: 32 checks, all pass. Feasibility-only solve ~3 s → ~4.4 s, still far inside its 60 s target |
| **ITC-2007 Track 3 — hard constraints** | **21 of 21 timetables violate none** | 2026-07-31 | ✅ **The claim `docs/testing-strategy.md` §1 makes first.** All four ITC-2007 hard constraints (Lectures, Conflicts, Availability, RoomOccupancy) re-derived from each instance and checked against the placements, never taken from CP-SAT's status. Seed 42, deterministic budget 60 per instance, production configuration. Total wall ~17 min |
| **ITC-2007 — the cost function itself** | **reproduces all 7 published solutions exactly** | 2026-07-31 | ✅ The archive ships solutions for comp01–07 produced by a third-party solver; `cost.py` re-evaluates them to exactly the cost its bundled report publishes — **all four components, all seven instances**. This is what makes every other figure in these rows checkable rather than self-consistent. Runs on every `run-checks.ps1` (no solver needed) |
| **ITC-2007 — cost vs the archive's published results** | **gap 255 %–9985 %, median 1269 %** on the 7 instances the archive gives figures for | 2026-07-31 | comp01 26 (best 5) · comp02 1035 (36) · comp03 531 (66) · comp04 479 (35) · comp05 1059 (298) · comp06 4034 (40) · comp07 852 (14). ⚠️ **Large, expected, and not a defect.** The strategy document states "the objective is not to beat published results"; the reference figures come from metaheuristics tuned for this exact problem, several with no time limit at all, against ~50 s of exact CP-SAT search here. **The model is demonstrably correct** — see the next row. The other 14 instances have no in-repo reference and are reported on validity alone |
| **ITC-2007 — evidence the model, not just the search, is right** | **comp11 solved to cost 0, proven optimal**; comp01 reaches the published optimum of **5** given more search | 2026-07-31 | Cost 0 is optimal by definition — no soft cost can be negative — and CP-SAT proved it. comp01 reached 5, equalling the best figure the archive records, when the same model was given roughly 8× the search (measured with `interleave_search` off, which does ~`num_workers`× more total work for the same per-worker budget). **The gap on the larger instances is search budget, not modelling.** Quote validity first, cost second, always with the budget |
| **ITC-2007 — reproducibility across runs** | **identical costs on all 21, twice** | 2026-07-31 | Two full sweeps, same seed and budget, on a machine whose load differed enough that per-instance wall clock moved by up to 2× (comp01 79 s → 41 s). Every one of the 21 costs matched. ADR-011's deterministic budget doing exactly what it was chosen for, on instances the project did not design |
| ⚠️ **`CpSolver.objective_value` vs the solution returned** | **disagreed on 2 of 21** (comp18, comp21), by 5–15 units | 2026-07-31 | Reported objective sat *above* the objective expression evaluated at the placements handed back, on solves that stopped before proving optimality. With `interleave_search = false` the two agree exactly on the same instances. **No figure anywhere depends on it** — every cost is re-derived by `cost.py`, and no score or ranking in the product reads `SolverOutput.cost`. Recorded in ADR-011; the two guards that could have gone flaky were pinned |
| **Full run through the API and the generation screen** | **COMPLETED in 105.3 s wall**, 3 distinct candidates, 0 duplicates, 218/218 placed each | 2026-08-01 | ⚠️ **Not comparable with the 147–150 s portfolio row below**: total budget **45**, `OPTIEDT_SOLVER_WORKERS=4` (set to keep the machine responsive during the check, not a product default), against that row's budget 90 at all workers. Reported deterministic 45.76 against 45 requested. Scores 79.82 / 79.79 / 79.62 — teacher-favouring, student-favouring, balanced. **student-favouring drove S2 to 0**, so the profiles do steer. What this measures is the *path* — launch, poll, score, render — not the engine, which has its own rows |
| **The complete Phase 4 path, end to end** | **a declaration reaches the solver and is honoured** | 2026-08-01 | T001 marked Monday 08:30 and Wednesday 15:40 unavailable on the grid; the generated Wednesday-14:00 row was withdrawn by the replace-wholesale rule and the rows came back marked `TEACHER`, while a teacher who declared nothing kept their `SYNTHETIC` rows. A run then placed T001's two sessions at slots 24/18, 21/22 and 25/22 across the three candidates — **never** at slot 0 or 14. This is the milestone's claim measured rather than asserted |
| **FR-18 room occupancy, rendered** | **matches `verify-instance` exactly, all four room types** | 2026-08-01 | The timetable screen's occupancy view sums to Amphi **32**, Salle **82**, Lab_Info **160**, Lab_Sciences **48** periods on the candidate it displays — the same figures `scripts/verify-instance.ps1` reports for the instance. Independent arithmetic (frontend, over placements) agreeing with the verifier is what makes the view trustworthy rather than merely plausible. ⚠️ It is the *period* figure; the bound that binds for laboratories is two-period windows, and the view says so on screen |
| **A budget too small to solve** | **run lands in `FAILED` carrying the reason** | 2026-08-01 | Total budget 3 (1 per profile) makes CP-SAT return `UNKNOWN`; `solver/engine.py` raises rather than reporting it as a normal result, the executor records `FAILED`, and the API surfaces the message. Correct behaviour, not a defect — and the C-13 lesson working: an `UNKNOWN` is never quietly passed off as an answer |
| **FR-19's trace — a published timetable's provenance** | **complete after a restart** | 2026-08-04 | Phase 5 M5. A real solve (seed 7, budget 90, 3 candidates, **206.9 s** wall) then `POST .../publish`; the API process killed; a **fresh process** returned run id, seed 7, all seven weights, `weekly.h1-h12.s2-s10`, budget 90 and 218 placements. ⚠️ The trace is ASSEMBLED from the run record on every read, never stored beside the publication - a second copy of the seed would be a second answer |
| **FR-11 — a teacher sees only its own** | **verified against the real API** | 2026-08-04 | M4, with real accounts from the seed command. Signed in as `t001`: own grid **200**, another teacher's grid **403**, `POST /runs` **403**. As `responsable`: both grids **200**. Anonymous: **401** everywhere but `/health` and `/auth/token`. A wrong password and an unknown username return identical 401s. In the interface, a teacher gets no Génération link and a read-only teacher field; the person in charge gets the 44-teacher dropdown |
| ⚠️ **`passlib` did not work at all** | **replaced with `bcrypt` directly** | 2026-08-04 | passlib 1.7.4 + bcrypt 5.0.0: `hash()` raised "password cannot be longer than 72 bytes" on every input, and version detection failed on the removed `bcrypt.__about__`. A DECLARED dependency from the scaffold that had never been exercised. Pinning bcrypt backwards to keep an unmaintained 2020 wrapper alive was the wrong direction |
| **FR-19 — a run survives a restart** | **verified end to end** | 2026-08-04 | Phase 5 M3. A run launched through `POST /runs`, the uvicorn process killed (connection refused confirmed), and a **fresh process** read it back complete: id, state, seed 42, budget, model version, all seven weights, a timezone-aware `createdAt`, the recorded error and all five pre-analysis checks. The row was confirmed present in the CONTAINER's database with `docker exec`, not merely at `localhost:5432` - which on this machine reaches a different server |
| **Store contract, both implementations** | **30 tests, one suite run twice** | 2026-08-04 | In-memory and PostgreSQL over the same assertions. ⚠️ It caught a real divergence on its first run: `InMemoryRunStore.save` replaced the whole record, so a recorded candidate could be overwritten - invariant 6 - while the SQL store refused. Fixed in `services/runs.py`. Two implementations of one contract drift silently unless something runs the same assertions over both |
| ~~**Diagnosis run — assumption literals**~~ | ~~inconclusive at reference scale~~ **SUPERSEDED, C-17 resolved** | 2026-08-04 | Phase 5 M2. Four computer laboratories withdrawn (an **area** contradiction, 160 periods against 112): a plain solve returns `INFEASIBLE` in **0.0 s**; the same model under four assumption literals returns **`UNKNOWN` after 240 s** at budget 120. Enforcement literals take `no_overlap`/`cumulative` out of presolve. The original pre-C-13 mix behaves the same way. **The mechanism is correct and tested — 14 tests naming exactly `('H1',)`, `('H12',)`, `('H3',)` on small instances — and unusable on this instance.** See C-17 |
| **Diagnosis run — deletion-based subset search** | **`('H3',)`, minimal, in 1.9 s** | 2026-08-04 | ✅ **Implemented** (C-17). The shipped `CpSatSolver.diagnose` on the reference instance with four computer laboratories withdrawn: one baseline solve establishes infeasibility, then each withdrawable rule is removed in turn. On the **contiguity** case (the original pre-C-13 mix) it returns **empty and NOT conclusive** in 60 s — the baseline solve cannot prove that infeasibility at all, which is exactly C-13, and the report says so instead of inventing a verdict. The pre-analysis catches that one in milliseconds |
| **Effective `y[s][t]` count after pruning** | **5,328** of 6,104 | 2026-07-30 | 87.3% of the upper bound. Start indicators `x[s,t₀]`: **4,720**. Together 10,048 variables (C-7) |
| **Cost of building the C-7 accounting** | **2.9–4.1 s → 7.6–8.0 s** | 2026-07-30 | Same configuration, three seeds; deterministic time 0.4–1.9 → ~6.1. Why `build_occupancy()` is called on demand and not by the feasibility solve |
| **First solve with the C-4/C-12 objective posted** | **~49 s wall · ~84 deterministic units**, feasible (not proven optimal) | 2026-07-30 | Seed 42, catalogue default weights, `deterministic_budget=30`, `num_workers=0`. 218/218 placed. ⚠️ The ~84 deterministic units against a budget of 30 is the **per-worker sum**, not an overshoot — see the two calibration rows above. This row previously read it as confirming a "calibration live again" risk that turned out not to exist |
| **Sub-scores, no objective vs. catalogue-weighted objective** | S2 65→2, S3 22→11, S4 45→52, S5 116→87, S6 1.76→1.53, S7 45→14, S10 104→139; score 78.0→**85.5** | 2026-07-30, after the S6 scale fix | Same seed (42). Every weighted criterion improves except S4; S10 (weight 0, never optimised for) degrades, which is expected multi-criteria behaviour. **Figures before the S6 fix were S2 19, S7 29, score 83.6** — the 28× over-weighting of S6 had been consuming search effort belonging to the criteria that actually carry weight (C-4) |
| **Objective auxiliary variables** | **5,249** under catalogue weights; **0** when every weight is zero | 2026-07-30 | Per criterion alone: S3 2,376 · S4 1,628 · S2 1,620 · S7 984 · S5 218 · S6 7 · S10 0. Closes the last open half of C-7 |
| **Normalised sub-score spread over 40 random placements** | S2 0.869–0.932 · S3 0.953–0.981 · S4 0.663–0.762 · S5 0.495–0.647 · S6 0.627–0.789 · S7 0.735–0.828 · S10 0.411–0.617 | 2026-07-30 | Bounds are **sound** (nothing left [0,1]) but **loose**, as ADR-009 accepts. ⚠️ S3's whole observable range is ~3 points of normalised scale, so at weight 0.15/0.9 it can move the score by at most ~0.5/100 — it is close to inert in the ranking. A tuning matter for Phase 4, not a correctness one |

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
- [x] **Three distinct candidates on the reference instance at production settings, each with its overall score and sub-scores** — met 2026-07-30. Three distinct candidates, 0 duplicates removed, each with all seven sub-scores (C-16). **C-5 resolved 2026-08-05**: the criterion is stated against the verified reference instance, while the general contract the software makes on any instance is "at most three, duplicates removed" (SRS Table 29, unchanged). ⚠️ The wording above changed with that resolution — it read "At least three candidates" and that form promised something the software cannot guarantee on an instance nobody has measured
- [x] **The sum of displayed contributions equals the score difference, to display precision** — met 2026-08-01, Phase 4 M5. The computation was verified 2026-07-30 (three real candidates, agreeing to 9 decimal places, plus a hypothesis property test); what was missing was *displayed*, and rounding happens in the component. `frontend/src/features/comparison/ContributionsTable.test.tsx` renders the table and reads the figures back out of the DOM. ⚠️ It caught a real defect: rounding each term independently does **not** preserve the sum — 2.7567 and −3.6663 show as 2.757 and −3.666, totalling −0.909 against a true difference of −0.910. Fixed with largest-remainder rounding, so each displayed term stays within one unit of the last place of its true value and the column adds up exactly
- [x] **Two runs with the same data, weights and seed produce the same candidates in the same order** — met 2026-07-30 at production settings, via `interleave_search` (C-16, ADR-011 amended). Verified on identical ids, order, placements, scores and sub-scores; guarded by `tests/integration/test_reproducibility.py`
- [x] **An instance without a solution produces a report naming the rules in conflict where CP-SAT can prove the infeasibility, and a pre-analysis report naming the resource and the quantity missing where it cannot** — met 2026-08-05, Phase 6 M3, **and the wording above carries the limit deliberately.** ⚠️ **The criterion was reworded rather than merely ticked**, by project-owner decision: measured on both shapes, it holds on one and not the other, and a tick against the original wording would have claimed something the product does not do. What *is* satisfied on both shapes is the phase's stated purpose — **a report rather than a timeout** — and the limit is measured, tested and documented rather than hidden. Same treatment as C-5: the wording moved, the implementation did not. On the **area** shape (computer laboratories withdrawn) the run reaches `DIAGNOSED` and names `('H3',)`, minimal and conclusive — criterion met. On the **contiguity** shape (the pre-C-13 mix) CP-SAT cannot construct the proof, stage 2 returns `UNKNOWN`, the engine refuses to pass it off as an answer, and the run lands in `FAILED` with the reason recorded — **no rule codes at all**, while the pre-analysis names `Lab_Info` short by 14 two-period windows and `Lab_Sciences` by 2. That is emphatically **not a timeout**, which is the phase's stated purpose, but it is not the criterion's stated wording either. `tests/acceptance/test_fr08.py` encodes **both** outcomes; writing only the first would let the suite report a capability the product does not have. It was left unticked as the conservative reading until the project owner decided it on 2026-08-05, which is what the tick above records. **Original note, still true:** built and measured Phase 5 M2's diagnosis answers `('H3',)`, minimal, in 1.9 s on the area case, but on the C-13 contiguity shape CP-SAT cannot prove the infeasibility at all and the report is honestly *inconclusive*, so the criterion **as literally worded** does not hold for every infeasible instance. ⚠️ Two lines in these documents claimed otherwise until 2026-08-05, saying Phase 5 moved three criteria and naming the conflict report among them; the arithmetic pins six as the total and two as Phase 5's contribution. **Phase 6 M3 settles this** by writing the acceptance test that decides what "met" means here — and it must not be written as though stage 3 always produces codes
- [x] **A teacher account obtains only its own availability and timetable** — met 2026-08-04, Phase 5 M4. Verified against the real API with accounts from the seed command: signed in as `t001`, own grid **200**, another teacher's **403**, `POST /runs` **403**; as `responsable`, both grids **200**; anonymous, **401** everywhere but `/health` and `/auth/token`. Which teacher the caller is comes from the TOKEN, which is the line Phase 4 explicitly left. `tests/integration/test_rbac.py` pins it against real tokens rather than an overridden dependency
- [x] **Closing a half-day in configuration removes those slots from every timetable, with no code change** — met 2026-08-05, Phase 6 M4. `tests/acceptance/test_fr09.py`: Wednesday afternoon closed by setting `Slot.is_open = False` and **nothing else**, the run launched through the API against the production solver, and no placement in any of the three candidates occupies a closed slot — occupancy checked, not the start index, since a two-period session could straddle one. All 218 sessions still placed. **"With no code change" is asserted rather than described**: the catalogue still holds exactly H1–H12, and the two instances differ in `Slot.is_open` alone — sessions, rooms, teachers, availability and constraints all identical, and every slot INDEX unchanged, which is what lets a shortened-day window shift displayed hours without moving a variable (ADR-003). ⚠️ **Not a formality on this instance**: any half-day closure costs each room one two-period window, and `Lab_Info` has exactly 8 spare across 8 rooms, so the closure takes it to **exactly 100.0 %** of its two-period windows. A solution exists only if a perfect packing does. Measured on three different half-days — it does
- [x] **The availability grid is completed without assistance by a user who had not previously seen it** — met 2026-08-07, **and the wording above was REWORDED rather than merely ticked**, by project-owner decision. ⚠️ **It read *"filled in under 5 minutes without training"*, and the run did not establish the time.** Same treatment as C-5 and as criterion 5 above: the wording moved, the implementation did not. **Built** 2026-08-01 (Phase 4 M6): two states, click or drag to toggle, whole week on one screen, closed slots not offered, generated declarations shown as generated. **What the run established:** the participant reached the grid, understood the task, marked unavailability and saved with **no assistance and no explanation given**, and judged the grid's functionality acceptable. ⚠️ **What it did not establish, and the reasons are recorded rather than hidden:** no time was measured, so *"under 5 minutes"* is unverified and the reworded criterion drops it; the participant was the **project owner**, who had not seen the *screen* (the frontend is not their code) but does know the domain, so the four comprehension questions in `demonstration.md` §2 could not be asked of them fairly; and the task was not isolated, since navigation and other screens were exercised in the same sitting. **No naive participant was available and the owner declined to involve one** — a recorded constraint on the evidence, not an oversight. ⚠️ **The same session reported the navigation confusing and pages not explaining their purpose.** That tension is deliberate: the grid passes, the product around it did not, and those are usability findings rather than FR-2 evidence. Full record and the protocol for a better second run: [`docs/demonstration.md`](demonstration.md) §2
- [x] **Every published timetable traces back to its run, seed and weights** — met 2026-08-04, Phase 5 M5. `POST /runs/{id}/candidates/{id}/publish` records the publication and `GET /publications` returns each with the trace ASSEMBLED from the run record — run id, seed, the whole weight vector, model version and deterministic budget. Verified on a real solve (seed 7, budget 90, 3 candidates, 206.9 s): the top candidate was published, the API process killed, and a **fresh process** returned the complete trace with all 218 placements. ⚠️ The trace is assembled, never stored beside the publication — a second copy of the seed would be a second answer, free to drift from the first
