# Open questions and errata

Findings from a full reading of the three specification documents, before any code existed.

**How to use this file.** If your work touches an open item, resolve it *here* first — with the reason
— then implement. An assumption made in code and never written down is how this project acquires a
defect that surfaces three weeks later.

Nothing in this file is a criticism of the specification. Three documents written in layers over four
weeks will disagree in places; the failure mode is not that they disagree, it is that nobody notices.

| Status | Meaning |
|---|---|
| **RESOLVED** | Decided, recorded in an ADR. Do not reopen without reading it |
| **OPEN** | Not decided. Do not silently pick an answer |
| **ERRATUM** | A document is wrong; replacement wording given |

---

## RESOLVED

### C-1 — The assistant's increment · RESOLVED → increment 1 · ADR-010

CdC §4.5 ("a committed part of the first increment"), CdC §7.4, CdC Table 2, the *Necessary* priority
of FR-22/23/24, PPM Table 6 (which lists increment 2 as exams + weights only), PPM §8.3 and PPM §10 all
place the assistant in **increment 1**. SRS §2.3 and SRS §1.2 place it in increment 2.

Eight statements against two. **Decision: increment 1.** The two SRS sentences are stale text from an
earlier draft — see the errata below.

**Carried forward:** PPM Table 8 allocates 3+5+3+4+2+3 = 20 days and names the assistant in **no
phase**. ~2.5 unbudgeted days ≈ 12% overrun. Tracked in `docs/status.md`. Release valve already decided
in PPM §8.3: the assistant's *report* is the first scope cut, explanations and answers kept.

### C-2 — Reproducibility vs parallel workers · RESOLVED → deterministic time · ADR-011

SRS §7.2 and acceptance test FR-19 require identical candidates for the same seed. PPM §4.5 runs the
optimisation with **all workers**. **CP-SAT under a wall-clock limit with parallel workers is not
reproducible** — workers race and a fixed seed does not fix it. As written, the requirement and the
acceptance test could not both hold.

**Decision: keep all workers, bound the solve by `max_deterministic_time`.**

Consequences, all documentation rather than code:
- The 60-second and 5-minute figures become **estimates, not wall-clock promises**. Both documents
  already hedge them as "objectives to be measured … not guarantees", so this narrows an existing hedge.
- A **wall-clock ceiling remains as a hang backstop**. Crossing it is an anomaly to log, not a normal exit.
- ⚠️ The deterministic-to-wall-clock ratio is **machine-dependent and must be calibrated on the
  reference instance in Phase 2**, then recorded in `docs/status.md`. Until then the user-facing limit
  is an unvalidated guess.
- The diagnosis run inherits the same treatment, which also gives it the budget it never had.

### C-3 — Normalisation bounds · RESOLVED → instance-derived · ADR-009

SRS §6.7 says bounds are "computed from the data of the run", ambiguous between the *instance* and the
*candidates produced*. The candidate-derived reading is excluded on three grounds:

1. **It breaks monotonicity**, which SRS §7.5 requires.
2. A run yielding two candidates degenerates to a 0 / 100 split.
3. **It silently invalidates cross-run comparison** — a regenerated candidate lives under a new run and
   would carry different bounds, so comparing it against the originals compares two scales. That is
   exactly what FR-23 exists to support.

**Decision: bounds derived from the instance, stable across every run on it.**

### C-8 — Who loads the department data · RESOLVED → the person in charge

CdC §3.1 puts data loading under the person in charge; CdC §4.3 and SRS §3.3 both say the administrator
does it; SRS Table 2 gives the person in charge read/write on **all** data and limits the administrator
to accounts and calendar.

**Decision: SRS Table 2 is authoritative.** The two flow sentences are imprecise prose.

**Related, unresolved but low-impact:** CdC Table 1 lists a fifth actor, **"Head of department"**
("examines the teaching loads and approves the timetable"), appearing in no other document with no
requirement, right, screen or acceptance test. **Treated as an out-of-system stakeholder.** Say
otherwise if the institution expects an approval step in the application.

---

## OPEN

### C-4 — The raw value of every soft criterion is undefined · **largest gap**

S2–S10 have codes, names and weights. **None has a measurement formula.**

`v_i(k)` feeds the score, the contributions, monotonicity, dominance and the weight learning. It is the
most load-bearing undefined quantity in the specification.

- S2, S4, S6 can partly inherit from the ITC-2007 curriculum-based definitions.
- **S3** (teacher idle), **S5** (preferred windows), **S7** (spread), **S10** (midday break) are
  project-specific with no published definition to lean on.
- **S6 has a dead half.** H5 already makes "room smaller than its group" impossible, so "over-used"
  must mean *utilisation rate* rather than over-capacity. The documents never say.

Each criterion also needs its `min_i`/`max_i` formula (C-3). Implement through the `Criterion` Protocol,
which requires `raw_value` and `bounds` **together** so a criterion cannot be half-defined.

**Blocks:** Phase 3 scoring and everything downstream. **Owner:** technical lead, before Phase 3.

### C-5 — "At least three candidates" can fail when duplicates are removed

SRS Table 29 says "at most 3, **duplicates removed**". CdC §11 requires "**at least three** candidates";
SRS §8.6 test FR-13 expects "**three distinct** candidates". PPM Table 10 anticipates the collision:
"candidates too similar … duplicates not presented twice".

If two profiles converge on the same timetable the system behaves **correctly** and the acceptance test
**fails**.

Options: (a) restate as "at least two distinct candidates, with profiles chosen so three distinct ones
are obtained on the reference instance"; (b) retain duplicates and flag them as identical.

**Blocks:** Phase 6 acceptance tests. **Owner:** technical lead, with the supervisor — it changes a
delivered acceptance criterion.

### C-6 — Redundant constraints corrupt the diagnosis report

**H2 is subsumed by H12** (NoOverlap over the whole promotion→group→subgroup hierarchy already forbids
what H2 forbids). **H11 is implied by H3** once `room[s]` is assigned, and duplicates pre-analysis check
#2 in arithmetic form.

Harmless for feasibility. **Not harmless for the diagnosis run**, whose entire value is naming the rule
the user must change. Overlapping assumption literals let the solver return either, so the report can
name a rule the user cannot act on.

**Decide explicitly which of H2 and H11 are posted as propagation aids *without* their own assumption
literal.** The mapping constraint → literal must be 1:1 and non-redundant.

**Blocks:** Phase 5 diagnosis run. **Owner:** whoever builds the solver.

### C-7 — The `y[s][t]` channelling constraint is unwritten

`y[s][t]` is up to 6,104 booleans — the dominant term in model size. **104 of the 218 sessions span two
periods**, so `y[s][t]` must mean *occupies* `t`, not *starts at* `t`. The constraint linking
`start[s]`, `iv[s]` and `y[s][t]` across a 2-period duration **appears in none of the three documents**.

Related: SRS Table 27 attributes H7 to `y`, but with `start[s]` an integer over a pruned domain each
session already has exactly one start — `y`'s real purpose is soft-constraint accounting.

Also unspecified: the **auxiliary variables the objective needs** (per-group-per-day first and last
occupied period, reified gap indicators) are absent from the model-size table, so the stated size is an
underestimate.

**Blocks:** Phase 2, the model. **Owner:** whoever builds the solver.

### C-9 — Four requirements have no detailed specification

**FR-6, FR-10, FR-17, FR-18** appear in the summary tables but have no input/processing/output row in
SRS §3.2. **FR-10 is missing entirely from the SRS Table 36 traceability matrix.**

Note: SRS Table 36 is nonetheless the only reliable place to reconstruct the FR numbering — the summary
tables in both CdC and SRS are damaged by cell-offset in the PDF layout, so codes and statements do not
line up when read literally.

**Blocks:** Phase 6 acceptance. **Owner:** technical lead.

### C-11 — The generated instance · **RESOLVED — it exists and it verifies**

**This finding was wrong, and is corrected here rather than deleted.** The scaffold originally recorded
the instance as missing and instructed the next session to write a generator reproducing it. It was
supplied on 2026-07-29 and is now in `data/instance/` — 13 CSVs, 36 KB.

**Every documented figure was re-measured and matches.** Not approximately — exactly:

| Claim | Documented | Measured |
|---|---|---|
| Sessions CM / TD / TP | 32 / 82 / 104 | ✅ 32 / 82 / 104 |
| Durations 1-period / 2-period | 114 / 104 | ✅ 114 / 104 |
| Groups PROMO / TD / TP | 6 / 15 / 30 | ✅ 6 / 15 / 30 |
| Rooms Amphi / Salle / Lab_Info / Lab_Sciences | 2 / 10 / 6 / 2 | ✅ 2 / 10 / 6 / 2 |
| Teachers by rank | 7 / 11 / 13 / 13 | ✅ 7 / 11 / 13 / 13 |
| Students · courses · slots open | 425 · 32 · 28 of 30 | ✅ 425 · 32 · 28 of 30 |
| Holidays, of which lunar | 18, 10 | ✅ 18, 10 |
| Availability rows · teachers covered | 157 · 41 of 44 | ✅ 157 · 41, all `SYNTHETIC` |
| Catalogue hard / soft · weight sum | 12 / 7 · 0.90 | ✅ 12 / 7 · 0.90 |
| **Verification 1** sessions without a room | 0 | ✅ **0** |
| **Verification 2** Amphi / Salle / Lab_Info / Lab_Sciences | 57% / 29% / **95%** / 86% | ✅ **57.1 / 29.3 / 95.2 / 85.7** |
| **Verification 3** over rank limit · heaviest | 0 · 12 periods (18 h) | ✅ **0 · 12 / 18** |
| **Verification 4** in difficulty · smallest margin | 0 · 11 free slots | ✅ **0 · 11** |
| **Verification 5** invalid refs · students matching | 0 · 425 | ✅ **0 · 425** |

The documentation's factual claims are therefore **verified, not merely asserted** — which is the
condition the whole "generated data is acceptable if verified" argument rests on (ADR-008).

**What remains of C-11:** the *generator* is still a stated deliverable (PPM §10) and does not exist.
That is now a documentation and reproducibility task, **not a blocker** — the instance it would produce
is already here and checked. Re-run the checks any time with
`scripts/verify-instance.ps1`.

### C-12 — S5 carries weight 0.20 and has no input data · **NEW, OPEN**

`teacher_availability.csv` has a boolean `is_available`, and **all 157 rows are 0** — they are
unavailability declarations, exactly as documented. There is **no representation of a preferred
window** anywhere in the instance schema.

But **S5 "Teacher preference" carries a default weight of 0.20 — the second highest of the seven
criteria** — and SRS §4.1 specifies an availability grid whose slots are marked "available,
unavailable **or preferred**".

Three ways this can go, and the choice is not obvious:

- **(a)** Add a third state (or a `preference` column) to `teacher_availability.csv` and have the
  generator produce some. Closest to the specification; changes the instance, so the documented row
  count of 157 must be restated.
- **(b)** Define S5 against something already present — e.g. distance from a teacher's declared
  unavailable block. Keeps the instance untouched but is not what "preferred window" means.
- **(c)** Accept that S5 measures 0 on this instance. **Cheapest and most dangerous.**

⚠️ **Why (c) is dangerous, and why this is worth resolving before Phase 3.** The three weight profiles
are balanced, student-favouring (raises S2) and **teacher-favouring (raises S3 *and* S5)**. If S5 is
identically zero, the teacher-favouring profile differs from the others by S3 alone — so it is weaker
than intended and **two candidates may well converge**.

That is precisely the **C-5** failure mode: duplicates are removed, fewer than three distinct
candidates are produced, and the acceptance test fails. It would fail for a reason nobody would think
to look for, because the visible symptom is "the portfolio is boring" and the cause is a missing
column.

**Blocks:** Phase 3 (scoring), and the availability grid in Phase 4. **Owner:** technical lead.

---

## Verification of the reference archives

**Confirmed the documented findings and sharpened two of them:**

- Kaggle's two invalid files are worse than "contains errors": **44% of timeslot rows have an end time
  at or before their start time**, and **83% of room+slot pairs are double-booked**. The archive's own
  note claims *"Clean CSVs"* — a direct vindication of verifying files rather than documentation.
- ⚠️ **New finding, not in the PDFs: `students.csv` carries names, emails, phone numbers and postal
  addresses** across 3,000 rows. This gives ADR-008's "rooms and enrolments only" a second
  justification beyond data quality, and it interacts with the data-minimisation requirement — no such
  field may ever reach the assistant's context payload.

### R-6 — The examination model breaks the `room[s]` schema

SRS §6.8 calls the examination model "the same construction with different variables". It is not: **an
examination may occupy several rooms at once**, so room assignment becomes a boolean matrix with a
capacity sum, not a single integer.

**Do not bake a single-room abstraction into shared solver code.** Increment 2, but the constraint on
the code structure applies now.

---

## ERRATA

Corrections to send in one pass rather than re-argue.

| Document | Current text | Should read |
|---|---|---|
| **SRS §2.3** | "Optional external service : interface towards a language model, **used only in the second increment** and deactivable by configuration." | "Optional external service: interface towards a language model, **part of the first increment**, deactivable by configuration." |
| **SRS §1.2** | "…and formulation of an explanation in ordinary language, **which constitute the second increment**." | "…**Generation of the timetable of an examination session and adjustment of the weights, which constitute the second increment.**" (the assistant is increment 1) |
| **CdC §4.5.1** | "…the weighted sum of **section 5.6**" | CdC §5 ends at 5.5. Should reference **SRS §6.7** / **PPM §4.6** |
| **CdC §4.1** | Lists both "AI assistant service" and "AI assistant module" | One entry. Same duplication in CdC §1.2, where "Assist in ordinary language" appears twice |
| **PPM §8.3** | Reduction order numbered **4–9** | **1–6.** "Item 4" currently has no referent |
| **CdC/SRS §4.5.2** | Grounding steps numbered **9–12** | **1–4** |
| **SRS Table 36** | FR-10 absent | Add: FR-10 → §4.1 → "Print or export a timetable view" |

### Not errors — recorded so they are not re-investigated

- **CdC Table 4 and Table 5 appear scrambled** when the PDF text is extracted: the code, statement and
  XHSTT-reference columns are offset by one row because of multi-line cells. Read with the offset
  corrected, they **agree exactly** with SRS Tables 27 and 28. There is no H-code or weight
  contradiction between the documents. The authority for both is `constraint_catalogue.csv`.
- **Soft codes skip S1, S8 and S9.** 12 hard + 7 soft = 19 matches the stated catalogue size, so the
  numbering is internally consistent. The gaps are unexplained — presumably criteria removed during
  revision. **S1, S8 and S9 are retired and must never be reused**, since codes are stable identifiers
  in the catalogue, the conflict report and `weight_delta` parameters.
- **X1–X4 and SX1 are not among the 19.** The catalogue covers the weekly model only.
- **The target semester is already past** (second semester 2025–2026; Ramadan window 18 Feb – 19 Mar
  2026). Correct for a demonstration instance. **Do not "fix" the dates.**
