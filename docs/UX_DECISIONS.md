# Why the interface is the way it is

[`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) says what the system is. This file says **why**, and it exists
for one reason: **most of these decisions look arbitrary from the outside and several of them fix a
defect that a plausible "improvement" would bring straight back.** Read the relevant entry before
changing a visual decision.

Each entry is: the decision, what it replaced, and the evidence.

---

## 1 · A grouped rail instead of a top nav

**Decision.** A 244 px left rail, three groups — *Timetabling*, *Inputs*, *Institution*.

**Replaced.** Eight flat links in a row across the top, distinguished by a 2 px bottom border.

**Why.** A row of eight equal links says only that there are eight of them. The three groups are the
three things a department actually does: produce a timetable, supply what goes into one, configure the
institution. The grouping answers "what is this product for?" at the same time as "where am I?".

⚠️ The rail decides what is **offered**, never what is **permitted**. Every endpoint checks the role
itself (FR-11). If `App.tsx` and the API ever disagree, the API is right.

---

## 2 · A sticky page bar carrying the single primary action

**Decision.** Every screen renders `<Page title subtitle status actions>`. The bar is sticky; `actions`
is one slot.

**Replaced.** The primary button lived inside the first of five stacked panels, so on Generate it sat
above four panels of results and scrolled away the moment a run produced output.

**Why.** "The CTA is hidden below the fold" is a structural problem, and making the button bigger does
not fix it. Because `actions` is a single slot, a screen physically cannot offer three equally-weighted
primary buttons.

⚠️ **The header belongs to the screen, not the shell.** A React context or a portal would have let
`App` own it, but then the title and the action would live apart from the state they describe, and a
screen rendered alone in a test would lose both.

---

## 3 · Sections, not cards

**Decision.** `.section` — margin and a heading, no box — is the default. `.panel` is reserved for a
genuine unit: a candidate, a publication, a printable sheet. Compare went from 5 panels to 0.

**Replaced.** Five to seven bordered white boxes per screen, on a ground only 2 % different from them.

**Why.** When the ground and the card are almost the same colour, the border is doing all the work
alone, and a stack of them is noise with corners rather than structure. V2 inverts the grounds —
tinted chrome, white content — which removes the need for a card to make content legible at all.

---

## 4 · Mono for figures and codes only

**Decision.** `--mono` on scores, hours, run ids, criterion codes, room codes, usernames, environment
variables. Sans everywhere else.

**Replaced.** Mono on eyebrows, nav group labels, badges, stat labels and table headers.

**Why.** The product's vocabulary genuinely is codes, and that made mono tempting everywhere. At that
density it stops signalling "this is a value you can compare" and just makes the product read as a
terminal. Restricting it gives it back its meaning.

Related: tabular numerals are set on `.num`, `.mono` and `table` rather than globally. V1 put them on
`body`, which widened the digits inside ordinary prose for no gain.

---

## 5 · No eyebrow-plus-hairline pattern

**Decision.** A section is introduced by a heading; the requirement code is a small chip beside it.

**Replaced.** `FR-15 · DECOMPOSITION` in 11 px uppercase mono with a rule trailing off to the right,
about twenty times across the product.

**Why.** Repeated at that density it labels nothing, and it is one of the clearest visual tells of a
generated dashboard. The code still earns its place — the specification, the catalogue and every
document in `docs/` argue in codes, so a screen that showed only prose would stop being checkable
against them — but it is demoted below the heading rather than sitting above it.

---

## 6 · The time axis is 116 px, and that number is measured

**Decision.** `--axis-w: 116px`, sticky-left, top-aligned, wrapping rather than clipping.

**Replaced.** 74 px with `white-space: nowrap` under `table-layout: fixed`.

**Why — this was a visible defect, not a preference.** `11:50–13:20` is eleven characters of mono and
does not fit in 74 px, so the label painted **on top of** the session cell to its right on every row of
every timetable, and print clipped the labels to `14:00–15:`.

⚠️ **The first fix failed, and that is the part worth remembering.** 100 px was chosen from the
arithmetic that eleven mono characters at 12 px is about 79 px. Re-measured in the browser, the real
inked width was **90 px** and it still overflowed. 116 px comes from measurement. The axis now also
wraps, so a longer label in some future instance degrades onto a second line instead of bleeding.

Verified: 0 of 5 labels overflow, and every axis cell's right edge abuts its row's first cell at
exactly 0 px — the axis is part of the table geometry, not text floating beside it.

---

## 7 · The availability grid does not shout

**Decision.** Available is a quiet fill with a small dot. Only *unavailable* is written.

**Replaced.** The word `AVAILABLE` printed into all thirty cells.

**Why.** A normal week is a teacher who is free almost everywhere, so the grid repeated one word thirty
times and the four cells carrying an actual decision disappeared into it. Available is the default
state; unavailable is the decision the teacher made, and only the decision needs a label. The
accessible name on every cell still says both, so a screen-reader user loses nothing.

---

## 8 · The candidate fingerprint

**Decision.** Seven bars per candidate row, one per soft criterion, height = normalised value.

**Why.** A run produces three candidates that can score within a tenth of a point of each other. The
score alone cannot show that they got there differently — which is the entire reason three weighting
profiles are solved. Seven bars make the difference visible before a number is read, and the full table
of terms is one press away for the reader who wants it.

⚠️ It ranks nothing and computes nothing. Every height is a value the API already sent; the bar is
typography applied to a figure, and the number beside it is the value.

---

## 9 · The decomposition ledger

**Decision.** Contributions as diverging bars either side of a zero axis, in the API's order, with the
sum shown landing on the score difference and the identity stated on screen.

**Why.** This is the product's central claim made visible. The ranking is defensible before a
department precisely because the difference decomposes *exactly*, and a plain table of numbers asks the
reader to take that on trust. The bars let them see direction before they read magnitude; the totals
let them check the arithmetic by hand.

⚠️ **Never sort by magnitude and never drop a near-zero term.** Sorting is the most tempting
"improvement" here and it breaks the correspondence between the table and the equation. A row missing
is a term missing.

⚠️ **One precision for every figure on the screen.** Two candidates at 79.8163 and 79.7943 display as
79.82 and 79.79 at two decimals; a head of department subtracts those and gets 0.03 while the
decomposition correctly totals 0.02. Nothing is wrong with either figure and the page still looks like
it cannot add up. `COMPARISON_DIGITS = 3` fixes that.

---

## 10 · Computed by OptiEDT ≠ Explained by AI

**Decision.** The assistant is docked beside the figures it explains. Every answer is preceded by its
origin label. The recommendation is badged **Computed recommendation** and names the rule that produced
it.

**Replaced.** The assistant as section five of seven in a vertical stack.

**Why.** Position is an argument. Below the figures, the model's prose reads as the conclusion; beside
them, it reads as an annotation on a result that already exists. And the label goes *above* the text
because a reader who reaches the end of a paragraph before learning a model wrote it has already read
it as fact.

⚠️ The computed form is the honest one, so the labelling protects the reader rather than the feature:
the computed answer is presented as a normal, complete answer — because that is what it is — not as a
degradation. See [`AI_BEHAVIOR.md`](AI_BEHAVIOR.md).

---

## 11 · The AI preamble is one line

**Decision.** One sentence carrying both guarantees, then answers.

**Replaced.** Eleven lines — a guarantee paragraph and a configuration notice — before a reader reached
any content at all.

**Why.** The guarantees genuinely matter, but a wall of explanation before the first answer signals an
unfinished feature apologising for itself. The full contract now lives on the answer label, where a
reader is actually deciding whether to trust a sentence.

Suggested questions became four short contextual actions in a stacked list rather than four full
sentences as wrapped pills of ragged widths.

---

## 12 · The run pipeline, and why `PENDING` explains itself

**Decision.** Three stages — *Data checks · Optimisation · Score & rank* — with diagnosis drawn as a
branch off the solve rather than a fourth step. When a run is `PENDING`, the screen says solves run one
at a time and why.

**Why.** A solve takes minutes. A spinner says only that something is happening; this says which of
three different things, and a reader who sees the solve has started also knows the data checks passed.
Diagnosis is drawn only when it ran, because a permanently visible fourth step teaches the reader that
diagnosis is part of every run.

⚠️ The `PENDING` explanation was added after launching two runs and watching the second sit on "Queued"
for minutes with an all-grey pipeline and nothing saying why. That reads as a hung application. Runs
execute on a single-worker pool deliberately — each solve already uses every core (ADR-005).

---

## 13 · Both long-running screens fall back to the newest server run

**Decision.** `/generate` and `/examinations` use `runId ?? latestFromServer`.

**Why.** `runId` is component state. Navigating to Compare and back lost a run the server still had,
and a solve left in flight came back as "No run yet" — the reader's own work, apparently discarded.
Found by driving the application, not by a test. The examination screen hit it first; the generation
screen had the same defect and the same fix.

---

## 14 · A disabled button is grey

**Decision.** `--sunk-2` ground, `--ink-4` text, full opacity.

**Replaced.** The whole button at 45 % opacity.

**Why.** On the sign-in screen the submit button is the largest coloured object, and a 45 %-opacity
ultramarine reads as a washed-out lavender — as the product's brand rather than as a state. Grey is
what "not now" looks like.

---

## 15 · The page bar is opaque

**Decision.** Solid `--surface`, no backdrop filter.

**Replaced.** `color-mix(paper 88%, transparent)` with `backdrop-filter: blur(8px)`.

**Why.** A translucent bar puts the title's contrast at the mercy of whatever happens to scroll under
it — a dark table header passing beneath turns a 16:1 heading into an unreadable one, and no static
audit catches it because it depends on scroll position.

---

## 16 · Landscape print, with the type code printed in every cell

**Decision.** `@page { size: A4 landscape }`, repeated table headers, forced session tints, and the
`CM`/`TD`/`TP` code as text in every cell.

**Why.** A six-day week on portrait A4 either loses Saturday or squeezes every column below the width a
course code needs. Browsers drop background colours by default, so the tints are forced through — but
an office printer is often grayscale anyway, which is why the left rule and the printed code carry the
meaning independently of the fill.

---

## 17 · Numbered steps only where the content is a sequence

**Decision.** The Generate empty state numbers four steps. Nothing else in the product is numbered.

**Why.** Numbered markers are a common decorative device. Here they are legitimate because the content
genuinely is ordered: you cannot compare candidates you have not generated, or publish one you have not
chosen. The empty state is also the only screen state guaranteed to be seen first, which makes it the
right place to teach the workflow.

---

## 18 · No CSS framework, and no UI library

**Decision.** Plain CSS in six token-driven layers.

**Why this was re-examined and re-confirmed.** Tailwind or shadcn would have meant rewriting the class
attributes of roughly forty components to reach a look the token layer already reaches — churn against
a "surgical frontend transformation" brief, with a new dependency to maintain and a generic-dashboard
aesthetic to fight. The V1 problem was never that the CSS layer could not express the design; it was
that the design was wrong. Tokens are infrastructure, not the aesthetic.
