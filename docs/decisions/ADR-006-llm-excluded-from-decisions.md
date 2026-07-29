# ADR-006 — The language model does not place, score or rank

**Status:** Accepted
**Date:** 2026-07-24 (specification phase)

## Context

The internship notes ask the AI to score and to rank timetables. The project integrates a hosted
language model. The question was not *whether* to use one, but **which tasks may be given to it**.

Four candidate uses were separated by a single test: **can the output be checked?**

| Use | Output checkable | Consequence of an error | Decision |
|---|---|---|---|
| Explain, compare, answer, report | Yes — every figure must appear in the supplied context | A sentence to be corrected | **Retained** |
| Suggest an improvement | Yes, once mapped onto the recommendation catalogue | A recommendation that gets refused | **Retained**, mapped |
| Compute a score or decide a ranking | **No** — the figure would come from the model | A number nobody can recompute | **Rejected** |
| Translate a sentence into a constraint | Only with a solver validating the model in a loop | **A timetable wrong without being detectably wrong** | **Out of scope** |

## Decision

**The language model explains, answers, phrases and reports. It never places a session, never computes
a score, and never decides an order.**

Scoring and ranking are computed exactly by the weighted sum of ADR-002. The model explains that
result, answers questions about it, and writes it up.

## Consequences

**The requirement from the internship notes is met in substance, and the figures stay verifiable.**
Both scoring and ranking are arithmetic: the department must be able to recompute a score by hand, and
the same data must give the same order twice. A language model offers neither property.

Concretely, the published evaluations of model-based scoring report **position, verbosity and
self-preference biases, with verdicts that flip when two candidates are simply swapped in the prompt.**
A figure obtained that way could not be defended before a department — which is the one thing this
system exists to make possible.

- Every figure the model states is checked against the context it received: `numbers(answer) ⊆
  numbers(context)`. A failing answer is discarded and the computed form shown instead.
- **The model never receives a database connection.** It receives a payload built by the application.
- **No decision the department must defend depends on this service.** That is precisely why the
  grounding check is allowed to be as limited as it is — see below.
- Everything works with the service switched off. Only text disappears.

**Be honest about the check's limits.** `numbers(answer) ⊆ numbers(context)` detects a figure the model
invented. It does **not** establish that the rest of the sentence is correct, and no requirement depends
on it doing so. The documentation says this rather than claiming more.

**On natural-language constraint entry.** Published approaches that succeed obtain their reliability
from **validating the generated model with a solver in a loop** — the reliability comes from the
harness, not the model. Building one does not fit four weeks. The recorded reason is **the absence of a
verification**, not a general distrust of language models.

## Alternatives considered

**Let the model score and rank as the notes literally request** — **rejected**: produces a number nobody
can recompute and an order that can change when two candidates are swapped in the prompt.

**Let the model edit a timetable directly** — **rejected**: breaks the separation the whole system rests
on. See ADR-007 for how the improvement loop is built the other way round instead.

**Constraint entry in ordinary language** — **out of scope**, for the reason above.

## References

Project Plan and Methodology §4.8 · Cahier des Charges §4.5, §4.5.1, §4.5.2 · SRS §6.11, §7.5
