# ADR-010 — The assistant is committed to increment 1

**Status:** Accepted
**Date:** 2026-07-29

## Context

The three specification documents disagree about which increment contains the AI assistant service.
This changes committed scope, so it cannot be left to inference.

**Increment 1** — eight statements:

| Source | Text |
|---|---|
| CdC §4.5 | "It is a **committed part of the first increment**" |
| CdC §7.4 | "The AI service belongs to the **first**" |
| CdC Table 2 | Increment 1 content includes "AI assistant service" |
| CdC Table 3 | FR-22, FR-23, FR-24 priority = **Necessary**, not "increment 2" |
| PPM Table 6 | Increment 2 = examinations + weights + NL-constraints. **The assistant is absent** |
| PPM §8.3 | Reduction order item 1: cut the assistant's *report*, "explanations and answers being kept" |
| PPM §10 | "AI assistant service: context builder, call to the language model API, and verification of the figures returned" — listed as a deliverable |
| SRS Table 36 | FR-22, FR-24, FR-25 traced to the assistant service alongside increment-1 requirements |

**Increment 2** — two statements, both in the SRS:

- §2.3: "Optional external service … **used only in the second increment** and deactivable by configuration."
- §1.2: "…formulation of an explanation in ordinary language, **which constitute the second increment**."

## Decision

**The assistant is committed to increment 1.** FR-22, FR-23 and FR-24 are built within the twenty days;
FR-25 (the report) is *Expected* rather than *Necessary*.

**SRS §2.3 and SRS §1.2 are errata.** Replacement wording is recorded in `docs/open-questions.md` so the
SRS can be corrected in one pass rather than re-argued.

## Consequences

The evidence is not close — eight to two, and the two dissenting sentences are consistent with an
earlier draft in which the assistant *was* increment 2. The same layered-revision signature appears
elsewhere in the CdC, which lists the assistant twice in §4.1 and "Assist in ordinary language" twice in
§1.2. That corroborates the stale-text reading rather than a deliberate change.

⚠️ **The schedule consequence must not be quietly absorbed.**

**PPM Table 8 allocates 3+5+3+4+2+3 = 20 days and names the assistant in no phase.** Phase 3 covers
scoring, ranking and the recommendation catalogue; Phase 4 covers the interface screens. Neither
mentions the adapter, the context builder, the answer verifier, the assistant panel or the report.

Realistic estimate: adapter + context builder + verifier ≈ 1.5 days, panel ≈ 0.5, report ≈ 0.5 —
**about 2.5 unbudgeted days, roughly a 12% overrun on a 20-day plan.**

This is tracked as a live risk in `docs/status.md` rather than absorbed silently. **The release valve was
already decided in advance**: PPM §8.3 makes the assistant's report the *first* scope reduction, with
explanations and answers kept. That the plan implicitly treats the assistant as small is consistent with
it being cut first if the estimate proves right.

**Consequences for the build:** FR-22, FR-23, FR-24 are increment-1 acceptance tests; degraded mode
(everything works with the service switched off) is an increment-1 requirement, not a later refinement;
and the provider-agnostic adapter and configuration flag exist from the first line of assistant code.

## Alternatives considered

**Follow the SRS and defer to increment 2** — **rejected**: it would require correcting six other
statements including three *Necessary* requirement priorities and a deliverables list, and would ship
increment 1 with computed explanations only, contradicting CdC §4.5's explicit commitment.

**Split — explanations and answers in increment 1, report in increment 2** — **not adopted as the
decision**, but effectively where the project lands if the schedule slips, since PPM §8.3 already names
the report as the first cut. Recorded so that outcome is understood as the planned degradation rather
than a failure.

## References

CdC §4.5, §7.4, Tables 2–3 · PPM Table 6, §8.3, §10 · SRS §1.2, §2.3, Table 36 · `docs/open-questions.md` C-1
