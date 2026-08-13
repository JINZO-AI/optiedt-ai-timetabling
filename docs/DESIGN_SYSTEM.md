# The OptiEDT design system (V2)

**Accepted as the product baseline on 2026-08-13.** This file records what the system *is*.
[`UX_DECISIONS.md`](UX_DECISIONS.md) records *why*, and several of its entries name a specific defect
that a plausible "improvement" would bring back. Read that file before changing anything here.

Plain CSS, no framework, no component library. Six layers, imported in this order by
`frontend/src/styles.css`:

| Layer | File | Answers |
|---|---|---|
| 1 | `styles/tokens.css` | What values exist |
| 2 | `styles/base.css` | What an unstyled element looks like |
| 3 | `styles/primitives.css` | The parts every screen is assembled from |
| 4 | `styles/shell.css` | The rail, the page bar, the content region |
| 5 | `styles/patterns.css` | The parts that belong to THIS product and no other |
| 6 | `styles/print.css` | What reaches paper (FR-10) |

⚠️ **Order is load-bearing.** A pattern may override a primitive; a primitive may override base.
Nothing may override tokens — a raw hex value in a component is a value the next palette change misses.

---

## 1 · Typography

**Self-hosted**, bundled by Vite from `node_modules` — no CDN, no third-party request, and the
interface renders identically on a faculty machine with no internet.

```
@fontsource-variable/ibm-plex-sans/wght.css     UI, prose, headings
@fontsource/ibm-plex-mono/{400,500,600}.css     figures, codes, identifiers
```

### ⚠️ The mono rule

`--mono` may be applied to: **a score, a count, an hour, a duration, a run id, a criterion or rule code
(`S2`, `H9`, `X1`), a room or group code, a username, an environment variable.** Nothing else.

V1 used mono for eyebrows, navigation group labels, badges and stat labels. At that density the product
read as a terminal rather than as institutional software, and it was the single most-cited reason the
first pass did not feel finished.

### Scale

| Token | Size | Used for |
|---|---|---|
| `--t-xs` | 12 px | table micro-labels, chips, hints inside dense rows |
| `--t-sm` | 13 px | dense table text, field labels, secondary prose |
| `--t-base` | 14 px | controls, table body, navigation |
| `--t-md` | 15 px | body prose — the default on `body` |
| `--t-lg` | 17 px | section heading |
| `--t-xl` | 22 px | page title in the bar |
| `--t-2xl` | 28 px | screen title on entry surfaces |

Figures get their own scale, because a score is the content and not a paragraph:

| Token | Size | Used for |
|---|---|---|
| `--n-sm` / `--n-md` | 14 / 18 px | inline figures, run vitals, dataset counts |
| `--n-lg` | 28 px | candidate score in the ranked list, the head-to-head delta |
| `--n-2xl` | 48 px | the two scores being compared |

Weights 400/500/600/700. Line heights `--lh-tight` 1.2, `--lh-snug` 1.35, `--lh-body` 1.6. Tracking is
negative on large type (`--track-tight` −0.02em) and open only on the one small-caps lockup
(`--track-caps` 0.06em, used by `.rail__tag` and nothing else).

Prose is capped at `72ch` on `p`, `70ch` on `.section__lead` and `.panel__note`, `74ch` on messages.

---

## 2 · Colour

Content sits on **white**. Tint is for *chrome* (the rail) and for *wells* (table heads, insets) —
never for a card floating on a card.

```
--ink      #10151c   headings, primary text
--ink-2    #262f3b   body
--ink-3    #4d5867   secondary
--ink-4    #5f6a78   ⚠️ THE FAINTEST TONE ANY TEXT MAY USE — 5.6:1 on white
--ink-5    #97a0ac   ⚠️ BORDERS, ICONS AND MARKS ONLY. NEVER TEXT

--surface  #ffffff   --page #ffffff   --chrome #fafbfc
--sunk     #f4f6f8   --sunk-2 #eef1f5
--line     #e3e7ec   --line-soft #eef1f4   --line-strong #c8cfd8
```

**One accent.** A second hue would compete with the status colours, and those carry meaning.

```
--accent #2249c9   --accent-hi #17369e   --accent-lo #3d63e0
--accent-tint #e7ecfb   --accent-wash #f4f6fe
```

**Status is reserved for meaning.** Nothing decorative may borrow it.

```
--ok   #0f6b45 / tint #e6f3ec        --warn #8a5308 / tint #fbf1e0
--bad  #ad1c1c / tint #fbeaea
```

**Session types** — ⚠️ colour is *redundant* encoding, never the only one. Every cell also prints its
type as text, so a reader who cannot separate the three hues still has a grid that reads.

```
CM  --cm #2249c9 / --cm-tint #edf0fc     lecture, the whole promotion
TD  --td #0d6e66 / --td-tint #e6f1f0     tutorial, one TD group
TP  --tp #8a5a10 / --tp-tint #f7efe0     practical, one TP group, in a laboratory
```

---

## 3 · Space, radius, elevation, motion

4 px base: `--s1` 4 → `--s11` 80. Every gap in the interface is one of these.

Radius `--r1` 3, `--r2` 6, `--r3` 10, `--r-full`. **Small on purpose** — a 16 px corner is a consumer
product; an instrument has edges.

Elevation is nearly absent: surfaces separate by rule and by space. `--shadow-1` is a hairline lift for
the active rail item; `--shadow-2` and `--shadow-3` exist only for things that genuinely float.

Control geometry is three heights and nothing else: `--h-sm` 30, `--h-md` 36, `--h-lg` 42.

Motion: `--dur-1` 120 ms, `--dur-2` 200 ms, `--dur-3` 320 ms, `--ease` and `--ease-out`.
⚠️ **Every animation is inside a `@media (prefers-reduced-motion: reduce)` guard**, and the duration
tokens themselves collapse to `0ms` under that query. What is animated: the live-run pulse, the ledger
bars growing from the axis, the candidate detail expanding, the assistant's thinking dots, the boot
line. Nothing else.

---

## 4 · Layout

```
--rail-w 244px    --bar-h 64px    --content-max 1280px    --axis-w 116px
```

`.app` is a two-column grid: the rail, then the workspace. `.rail` is sticky full-height with a tinted
ground. `.topbar` is sticky, **opaque**, and carries the title, subtitle, live status and the screen's
single primary action. `.content` is capped at 1280 px and centred.

Three content shapes, and a screen picks one rather than stacking panels:

- **`.split`** — main column plus a 372 px companion rail that scrolls inside itself. Used by Compare
  to put the assistant beside the figures it explains.
- **`.duo`** — two equal columns for two things being compared.
- **`.trio`** — an auto-fitting row of cards, minimum 220 px.

Breakpoints: **1240** (split stacks, aside stops being sticky), **900** (rail becomes a horizontally
scrolling strip above the content — no drawer, no state to manage, nothing to trap focus in),
**560** (page bar wraps, padding tightens).

---

## 5 · Components

**`.section`** is the default grouping: margin and a heading, no box. **`.panel`** is a bordered card
and is used only for a genuine conceptual unit — a candidate, a publication, a printable sheet.

**`.section__title`** carries the requirement code beside it as a demoted `.section__code` chip
(`Where the difference comes from · FR-15`) rather than above it as an eyebrow.

**Buttons.** One primary per screen, in the page bar. `.secondary` (outline), `.ghost`, `.danger`,
`.link`. ⚠️ **Disabled is grey**, not a translucent accent — `--sunk-2` ground, `--ink-4` text, full
opacity.

**Fields.** Sentence-case labels at 13 px in `--ink-2`; hints at 13 px in `--ink-4`; 36 px controls;
focus is a 2 px accent ring at 2 px offset via the global `:focus-visible`.

**Badges** are sentence case (`Completed`, `Queued`) with tone modifiers `--ok/--warn/--bad/--run/--idle`.
`--run` carries a pulsing dot and means one thing: work is happening on the server right now.

**Messages** — `.error`, `.warning`, `.success`, `.note` — carry a 3 px rule down the leading edge, so
colour is never the only signal.

**`.empty`** is a centred instruction, not a boxed apology.

---

## 6 · Tables

One system. Sticky tinted header, hairline under every row, a heavier rule under the head, hover on
`--chrome`, figures right-aligned in mono. Any table wider than its column scrolls inside
`.table-scroll` or `.gridwrap`; the page never scrolls sideways.

### The weekly grid

The most important surface in the product.

- `.gridwrap` is the scroll container **and** the rounded frame. It is what lets the header row stick
  to the top and the time axis stick to the left while a six-day week scrolls.
- **`.grid__hour` is `--axis-w` = 116 px, and that number is measured.** ⚠️ V1 gave it 74 px with
  `white-space: nowrap` under `table-layout: fixed`; `11:50–13:20` is wider than that, so every label
  painted over the session cell beside it and print clipped them to `14:00–15:`. A first fix at 100 px
  still overflowed, because the real inked width is 90 px, not the 79 px the arithmetic predicted.
  The axis also **wraps rather than clipping**, so a longer label degrades instead of bleeding.
  **Measure before changing this.**
- Cells are 76 px, top-aligned. A busy cell carries a 3 px left rule in its type colour, the course
  code in mono, the type as a printed chip, and the two dimensions the current view is not filtered by.
- A closed slot is **drawn as closed** — hatched — rather than omitted, so the week keeps its shape
  (ADR-003, invariant 7).

### The availability grid

⚠️ **Only the declared state is written.** Available is a quiet green fill with a dot; unavailable says
so. V1 printed `AVAILABLE` into all thirty cells, which shouted one word across the whole grid and hid
the four cells that carried an actual decision. The accessible name on every cell still says both.

---

## 7 · The signature: the decomposition ledger

Because the score is a weighted sum of normalised values,

```
score(A) − score(B) = 100 × Σ ( wᵢ × ( nᵢ(A) − nᵢ(B) ) )
```

holds **exactly**. The ledger draws each term as a bar either side of a shared zero axis, in the
table's own order, with the weight and both normalised values beside it, and shows the sum landing on
the difference. A `✓ Σ contributions = Δ score` line states the identity on screen.

⚠️ **Never re-order by magnitude and never drop a near-zero term.** A row missing from this table is a
term missing from an equation a department is invited to check by hand. `roundPreservingSum` uses
largest-remainder rounding so the displayed column adds up at the displayed precision.

Two `.ledger-highlight` lines name the largest positive and largest negative term. That is *selection*,
not computation — the presentation layer may filter, and every figure still comes from the API.

**The candidate fingerprint** is seven bars, one per soft criterion, each as tall as its normalised
value. It ranks nothing; it lets a reader see that two candidates a tenth of a point apart got there
differently, before reading a number.

---

## 8 · The assistant panel

Docked **beside** the figures it explains, never below them. Dark header, a one-line contract, then
answers. Every answer is preceded by its origin label — `.assistant__origin` for the computed form,
`.assistant__origin--generated` for a written one — because a reader who reaches the end of a paragraph
before learning a model wrote it has already read it as fact. See [`AI_BEHAVIOR.md`](AI_BEHAVIOR.md).

---

## 9 · Print (FR-10)

`@page { size: A4 landscape; margin: 14mm 12mm 12mm }` — a six-day week on portrait A4 either loses
Saturday or squeezes every column below the width a course code needs.

The shell, tabs, controls and the assistant are hidden. `thead` repeats with
`display: table-header-group`. Sticky is forced off — it can paint over the row beside it on paper. The
axis gets 22 mm and is allowed to wrap. Session tints are forced through with `print-color-adjust:
exact`, **and** the left rule and the printed type code carry the meaning on a grayscale printer.

---

## 10 · Accessibility conventions

- **`--ink-4` is the text floor.** Measured: 0 contrast failures across 545 text nodes on 7 routes.
- Colour is never the only encoding — session type also prints its code; the active rail item has a
  fill *and* a marker; messages carry a leading rule.
- `:focus-visible` paints a 2 px accent ring at 2 px offset on every interactive element. No focusable
  element sits inside an `overflow: hidden` ancestor close enough to clip it.
- A skip link, a `<main id="main">` landmark, `aria-current` on tabs and rail links, `aria-expanded` on
  disclosure buttons, `role="img"` with a full text alternative on the fingerprint, `role="checkbox"`
  with `aria-checked` and a descriptive `aria-label` on every availability cell.
- `prefers-reduced-motion` collapses every duration token to zero and disables every keyframe.
