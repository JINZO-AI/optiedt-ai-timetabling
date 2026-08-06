# AI integration

This is the part of the system most likely to be implemented wrongly, because the obvious reading of
"the AI improves the timetable" is the one thing it must never do.

Two components, both tightly bounded:

- **Recommendations** — a closed catalogue of three actions that change what the solver is *asked*, and
  trigger regeneration through the same engine.
- **The assistant** — a language model that reads computed figures and returns text.

Neither places a session. Neither computes a score. Neither decides an order.

---

## Where intelligence sits, and why

The system contains two decisions of different natures. The assignment of sessions **admits no error**:
a timetable with a conflict cannot be published whatever its other qualities. The choice among valid
timetables is a question of compromise: an error there produces a worse ranking, not an unusable
result.

**Methods that guarantee go on the first. Methods that learn go on the second.**

Constraint programming — retained for the first — *is* artificial intelligence in the accepted sense:
it belongs to the symbolic branch of the discipline, that of constraint satisfaction problems. The
project uses AI at both levels, of two different kinds, and names them separately rather than using one
word for both.

| Responsibility | Technique |
|---|---|
| Assigning sessions to slots and rooms | CP-SAT |
| Respecting hard constraints | CP-SAT, guaranteed by construction |
| Reducing soft penalties | CP-SAT under a time limit |
| Detecting impossible situations | Arithmetic verification before solving |
| Naming rules in conflict | Solver infeasibility explanation, separate run |
| Diversity of candidates | Repeated solving under distinct weight profiles |
| Score, order, decomposition | Weighted sum of normalised criteria — exact |
| Adjusting weights to the department | Supervised learning on recorded comparisons *(increment 2)* |
| Explanation, questions, reports | Hosted language model on already-computed figures, under validation |

---

## Recommendations — a closed catalogue of three

A recommendation is **never a timetable edit**. It is a change to one of three inputs the solver
already accepts.

| Action | Parameters | Effect on the next run |
|---|---|---|
| `weight_delta` | criterion code, new weight | Replaces one weight of the profile that produced the candidate |
| `lock_session` | session id | Fixes `start[s]` and `room[s]` to their current value, as H10 |
| `exclude_slot` | session id, slot id **or** room id | Withdraws one value from the domain of `start[s]` or `room[s]` |

These three identifiers are used throughout the specification and must not be renamed.

### The regeneration loop

```
candidate  ──►  analysis layer scores it against the criteria
                        │
                        ▼
           finds a criterion carrying most of the gap
                        │
                        ▼
           recommendation, status = proposed
                        │
        ┌───────────────┴───────────────┐
     accepted                       refused
        │                               │
        ▼                               ▼
  new run, one input changed      status = rejected
        │                         candidate unchanged
        ▼                         no run created
  SAME CP-SAT engine  ──► new candidate, scored and ordered like any other,
                          linked to the recommendation and the original run
```

**Why the guarantee carries over.** The hard constraints H1–H12 are declared identically in the
regenerated run, so they hold in the new candidate **for the same reason they held in the first one**.
Nothing is edited by hand and nothing is edited by the AI. A recommendation can only change what the
solver is *asked to do*, never what a solver call is *allowed to return*.

The marginal engineering cost is small: the portfolio mechanism already loops over several inputs to
produce several candidates, and a recommendation simply adds one more input to that loop.

✅ **Built in Phase 7 M2 (FR-23), 2026-08-06.** `services/regeneration.py` assembles the new run;
`POST /runs/{id}/candidates/{id}/regenerate` returns **202 and a new run id**, exactly like `POST
/runs`, because that is what it is. Three things were decided before the code and are worth carrying:

- **Overrides compose.** A regenerated run carries its origin's locks and exclusions **plus** the new
  one (C-20). Without that, accepting a second recommendation would silently discard the first, and a
  user would watch a lock they set disappear with nothing on screen to explain it.
- **A `weight_delta` steers the search, not only the scoring.** The regenerated run's three profiles
  are derived from its own adjusted weight vector rather than from the catalogue. Deriving from the
  catalogue would re-score an unchanged timetable — a recommendation about nothing.
- **A lock RESTRICTS; it never grants.** H10 intersects the pruning H4/H5/H6/H8/H9 already did, so an
  accepted recommendation cannot place a session on a closed slot or in a room too small for its
  group. `build_variables` raises naming the rule that refused.

### The catalogue is closed on purpose

A recommendation that cannot be expressed as one of the three actions is **not offered**, rather than
approximated. Type it as a union — `WeightDelta | LockSession | ExcludeSlot` — so that adding a fourth
variant is a type error wherever the union is exhaustively matched, not a convention someone can
quietly break.

---

## The assistant

An adapter around an external language model API. **Stateless between calls. Holds no database
credential.** Reached through a provider-agnostic client and switchable off by configuration.

### What it does

- Explains in ordinary language why a candidate scores as it does, and where its weaknesses are.
- Answers a question about a candidate or a published timetable.
- Phrases the recommendations produced by the analysis layer.
- Drafts a readable report on a run and the candidate retained.

### What it does not do

- **It never places a session and never writes into a timetable.**
- **It never computes a score and never decides a ranking.** Both are arithmetic: the department must
  be able to recompute a score by hand, and the same data must give the same order twice. Published
  evaluations of model-based scoring report position, verbosity and self-preference biases, with
  verdicts that flip when two candidates are simply swapped in the prompt. A figure obtained that way
  could not be defended before a department.
- **It never receives the database.** It receives a payload built by the application.

The internship notes ask the AI to score and to rank. The requirement is met **in substance**: the
platform computes both exactly, and the model explains the result, answers questions about it and
writes it up. The figures stay verifiable. (ADR-006.)

### Context construction

For each request the context builder assembles a JSON object containing **only what is needed to
answer, and nothing else**.

| Request | Context supplied | Size |
|---|---|---|
| Explain a candidate | Sub-scores, normalised values, weights in force, overall score | One candidate |
| Compare two candidates | Both sets of sub-scores and the contributions | Two candidates |
| Answer a question | Placements concerned, scores of the run, calendar in force | Bounded by the run |
| Produce a report | Run parameters, all candidates with scores, the published timetable | One run |

**Data minimisation.** The payload carries aggregated figures, codes and labels. **No student name, no
teacher email address, no personal identifier leaves the institution.**

### Verification of the answer

Every numeric token in the answer is compared against the numbers present in the context:

```
numbers(answer) ⊆ numbers(context)
```

If the inclusion does not hold, **the answer is discarded and the computed form is displayed
instead**. The same fallback applies when the service errors or exceeds its timeout.

**Be honest about what this check does.** It detects a figure the model invented. It does **not**
establish that the rest of the sentence is correct, and no requirement depends on it doing so. That
limit is precisely why no decision the department must defend rests on this service.

### Suggestions are not executable

A suggestion phrased by the assistant is matched against the recommendation catalogue before being
offered. **A suggestion matching no action type is displayed as a remark and carries no control to act
on it.** Same discipline as everywhere else here: the system proposes only what it can carry out
through the solver.

---

## Degraded mode

If the service is unreachable, refuses, times out, fails a check, or is switched off in configuration:

- **Generation, scoring, ranking, comparison, regeneration and publication remain available in full.**
- Explanations and reports fall back to their computed form.
- Only text disappears.

This is an acceptance test, not an aspiration: switch the service off in configuration and confirm
every other function is unaffected.

---

## Excluded: constraint entry in ordinary language

Translating a sentence into a constraint model is **out of scope**, and the reason is recorded so it is
not revisited casually.

Published approaches that succeed at this obtain their reliability from **validating the generated
model with a solver in a loop** — the reliability comes from that validation harness, not from the
model. Building such a harness does not fit the duration of the project.

The consequence of getting it wrong is what makes it disqualifying: a sentence understood incorrectly
produces **a timetable which is wrong without being detectably wrong**. Every other use of the language
model here has a checkable output; this one does not.

The recorded reason is **the absence of a verification**, not a general distrust of language models.

---

## Non-functional requirements

- **Grounding** — every figure produced by the model is checked against the context supplied. A figure
  absent from that context is not displayed.
- **Independence** — if the service is unreachable, only the text disappears.
- **Confidentiality** — the context carries identifiers, scores and placements; no student name and no
  personal datum beyond the account of a teacher already responsible for a session.
- **No free text in decisions** — the service receives a structured explanation and returns a sentence;
  the content of that sentence enters into no calculation.
- **Latency** — an explanation or answer returns within a configurable timeout, defaulting to 10
  seconds, beyond which the computed form is shown. The request is asynchronous so the interface is
  never blocked.
- **Human control** — no timetable becomes visible to teachers and students without an explicit act of
  publication by the person in charge.

---

## Increment and schedule

The assistant is **committed to increment 1** (ADR-010). SRS §2.3 and §1.2 place it in increment 2;
those two sentences are errata, contradicted by eight statements across the other documents and by the
*Necessary* priority of FR-22, FR-23 and FR-24.

⚠️ **The 20-day phase plan allocates the assistant no days in any phase.** Adapter, context builder,
verifier, panel and report are realistically ~2.5 days — about a 12% overrun. Tracked in
`docs/status.md`. The release valve, already decided in advance: the assistant's **report** is the
first thing cut under time pressure, with explanations and answers kept.
