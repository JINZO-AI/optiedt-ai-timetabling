# ADR-012 — A dataset replacement refuses rather than orphan an overlay

**Status:** Accepted
**Date:** 2026-08-11

> ⚠️ **Project decision — determined from repository evidence and engineering research because
> supervisor clarification was unavailable.** Nothing here is attributed to the supervisor. The
> requirement it serves, FR-1, *is* supervisor-written (SRS §3.2 Table 4); what this ADR settles is a
> question the specification does not raise at all.

## Context

FR-1 says *"load and manage the data of the department"*, and SRS §3.2 Table 4 gives it an
input/processing/output row: *files or forms validated by the server* → *verification of the types and
of the references, then recording* → *entities recorded and report of the rejected lines*.

**The specification never says what happens on the SECOND load.** Two other requirements already store
statements *about* the department's data, layered over it at run assembly
(`docs/architecture.md`, "The instance a run is assembled from — layers, not edits"):

- **FR-2** — a teacher's availability declaration, keyed by teacher and slot index.
- **FR-9** — the administrator's calendar, keyed by slot index.

Replacing the base can leave either pointing at something that no longer exists. Investigation of the
running code established what happens today, and the answer is the worst available one: **nothing
fails, anywhere.** `solver/variables.py::unavailable_by_teacher` builds a map and reads it with
`.get(session.teacher, frozenset())`, so a declaration naming a departed teacher is never consulted;
`preanalysis` iterates `instance.teachers`, so it never sees one either; and
`services/calendar.apply_calendar` iterates the *new* instance's slots and consults the stated map only
for slots it finds, so an orphaned closure is discarded without trace. No exception is raised at
import, at effective-instance construction, at pre-analysis, or during a solve. **The statement simply
stops meaning anything, silently** — which is the *"wrong rather than absent"* class of failure this
project treats as worse than a crash (`preanalysis/verifications.py::GroupHierarchy`).

## Decision

**A dataset replacement is rejected if it would leave an existing persisted FR-2 declaration or FR-9
calendar override invalid or orphaned. Existing overlay data is never silently deleted. The existing
dataset remains active when compatibility validation fails. A successful replacement preserves
referential integrity and is committed atomically.**

Four points make it checkable against code:

1. **Compatibility is judged on the COMPLETE EFFECTIVE DATASET** — the candidate with the stored
   calendar and the stored declarations applied — not on the raw supplied base.
   `services/dataset.check_compatibility` builds it with the same `apply_calendar` and
   `apply_declarations` a run would use.
2. **FR-9 needs a SECOND, separate check, and it cannot be folded into the first.** `apply_calendar`
   swallows an orphaned closure, so the effective dataset looks clean while the administrator's
   statement has been silently deleted — exactly what this decision forbids.
   `_closures_that_would_be_orphaned` compares the stated slot indices against the candidate directly.
   `unit/test_dataset.py::test_an_orphaned_closure_is_invisible_in_the_effective_dataset` asserts that
   invisibility, so the second check cannot be removed as redundant.
3. **An inert declaration marker must not block.** The SQL store keeps a `-1` row so that "asked and
   answered nothing" stays distinct from "never asked". A teacher whose grid was emptied is still named
   by `declared_teachers()` while contributing no availability row. Judging on the effective rows
   rather than on that set is what keeps the one escape route open — see the consequences.
4. **Withdrawal takes the same check.** `DELETE /api/dataset` restores the reference files, which is
   itself a base change and can orphan a statement the imported dataset made possible.

## Consequences

**What it costs.**

- **A replacement can be blocked by data the importer cannot clear themselves.** The person in charge
  *can* empty any teacher's grid (`_require_own_grid` returns early for every role but `TEACHER`), but
  `DELETE /api/calendar` is the administrator's. A calendar-caused refusal needs a second actor. That
  is SRS Table 2's division of rights, not a defect, and the response says so in its `remedy` field.
- **On a fresh installation the rule is vacuous** — no declarations, no calendar — so it costs the
  primary path nothing. It governs only re-loading.

**What made it necessary rather than merely tidy.**

- **It is the missing half of a rule the application already enforces.** Neither overlay can be
  *created* pointing at something absent: `routers/availability` answers 404 for an unknown teacher and
  422 for an unknown slot, and `services/calendar.build_overrides` raises `CalendarError` for an unknown
  slot index. A base change was the only remaining way to manufacture an orphan.
- **It keeps atomicity achievable.** Each store owns its own session, so **no transaction spans two of
  them**. An import that cleared declarations could not be atomic with the write that replaced the
  dataset. Refusing keeps the write set to one row of one store, in one transaction
  (`db/repositories.SqlDatasetStore.save`), with validation and compatibility both completing before it
  is reached — so a refused import has nothing to roll back because no transaction was opened.

**⚠️ Two limitations, recorded rather than absorbed.**

1. **A slot whose index survives but whose meaning changes is undetectable.** If the new dataset numbers
   slot 7 as Tuesday period 2 where the old one had Monday period 3, every check here passes and the
   administrator's closure now closes a different half-day. Detecting it needs a slot identity the
   model does not have, and inventing one is a larger change than FR-1 asks for.
2. **There is no protection against a concurrent write.** A declaration saved between the compatibility
   check and the replacement is not seen by the check. The repository has no locking of any kind, the
   specification asks for none, and building one for this path alone would be new architecture.

## Alternatives considered

| Rejected | Why |
|---|---|
| **Cascade — delete the orphaned declarations and closures** | It destroys a statement a person made, without asking. PostgreSQL — this project's own database — makes `NO ACTION`/`RESTRICT` the *default* referential action and requires `CASCADE` to be asked for explicitly; nothing here asks for it. It would also need a cross-store transaction that does not exist |
| **Import anyway and leave the orphans** | This is today's behaviour, and it is the reason the ADR exists: the orphan is silently ignored by the solver, the pre-analysis and the calendar alike. A department would keep a closed half-day that quietly reopened |
| **Judge compatibility on the raw supplied base only** | Misses the FR-2 case entirely. An orphan lands in `instance.availability` through `apply_declarations`, which the raw base does not contain |
| **Judge compatibility on the effective dataset only** | Misses the FR-9 case, because `apply_calendar` discards an orphaned closure before it can be observed. This is the alternative that looks correct and is not, which is why point 2 of the decision carries its own test |
| **Require `declared_teachers() ⊆ the new dataset's teachers`** | **Deadlocks.** `AvailabilityStore` has no delete and no endpoint forgets a declaration, so a teacher who has left would block every future import for good, recoverable only by direct SQL |

## What would reverse it

A supervisor statement about what a second load does to existing declarations and closures, or a
requirement for unattended/scripted import where refusing is worse than losing an overlay. Both would
be new information; neither exists today.
