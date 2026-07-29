# ADR-003 — Institutional calendar rules as configuration, not constraints

**Status:** Accepted
**Date:** 2026-07-23 (specification phase)

## Context

An institution applies rules that change the grid of available moments: certain half-days are not used
for teaching, the working day is shortened during a declared period (in particular Ramadan), and the
calendar contains fixed holidays alongside lunar holidays whose dates are known only approximately in
advance.

These could have been written as constraints of the model. The reason they are not is an engineering
one, not a matter of convenience.

## Decision

**Held as configuration data, acting through mechanisms the model already contains.**

Exactly two effects:

- **Closing slots.** A closed half-day sets `Slot.is_open = 0`. **H9 — which already forbids closed
  slots and holidays — then removes them from the domain of every session.** No new rule is written.
- **Shifting hours.** A shortened-day window shifts each period's start and end hour by a configured
  number of minutes. **The slot index does not change**, so no variable and no constraint is affected;
  only displayed and printed hours differ.

## Consequences

**A rule written into the model cannot be changed by the department. A rule held as data can.**

That is the whole argument. These rules are decided by the institution, differ between establishments,
and change from year to year — **Ramadan moves about eleven days annually**, and which half-days are
closed is a local decision. Writing them into the model would oblige the department to call a developer
in order to apply a decision it had itself taken.

- **Closing a half-day in configuration removes those slots from every timetable produced, with no code
  modification.** This is an acceptance criterion, not an implementation detail.
- The application can be reused the following year by editing data.
- Adding a CP-SAT constraint for Ramadan or a closed Saturday **is a bug**, not a feature.

**The cost, stated as plainly as the benefit:** a rule held as data can be modified by anyone with
administration rights, **including by mistake**. Configuration is the safer of the two options only
while the rule is genuinely institutional rather than absolute.

**The condition for promotion.** If the institution confirms **in writing** that a rule of this kind
must never be violated under any circumstance, it is promoted to a hard constraint and receives its own
code in the catalogue. Until that confirmation is obtained, configuration is the safer choice.

## Alternatives considered

**Writing them as hard constraints H13, H14, …** — **rejected** for the reason above: it transfers
control of an institutional decision from the institution to the developer, for rules that are known in
advance to change.

**Hard-coding the Tunisian calendar** — **rejected**: the lunar dates are approximate until close to the
date, and the application is meant to be reusable by another institution.

## References

Project Plan and Methodology §5.5, §2.3 · Cahier des Charges §5.2 · SRS §6.3
