# What the AI does, and what it is forbidden to do

**The language model explains. It decides nothing.** That is ADR-006, and it is the reason the feature
was admissible at all in a system whose output a department has to defend.

See also: `docs/ai-integration.md` (the design), ADR-006, ADR-007, ADR-010, and C-21 in
`docs/open-questions.md`.

---

## 1 · Where it is used — three endpoints, one screen

| Endpoint | What it produces |
|---|---|
| `GET /api/assistant/runs/{run}/candidates/{cand}/explanation` | Why this candidate scores as it does |
| `POST /api/assistant/runs/{run}/question` | An answer to a free-text question about the run |
| `GET /api/assistant/runs/{run}/report` | A readable report on the run |

All three surface in one place: the **assistant panel** on `/compare`, docked beside the ledger. The
report is requested on demand rather than loaded with the page.

⚠️ **The routes are registered whether or not the service is switched on.** Gating them on
`assistant_enabled` would make the interface 404; the specified behaviour is that only *text*
disappears (invariant 5), so they answer 200 with the computed form instead.

---

## 2 · What the model receives

A **context payload** built by `assistant/context.py` from figures the analysis layer already computed:
the candidate's score and sub-scores, the criteria and their weights, the run's parameters, and — for a
comparison — the decomposition terms.

⚠️ **The assistant never receives a database connection** (invariant 4). It cannot query, browse or
discover anything. It sees a payload and returns text.

⚠️ **No student, teacher or account personal data is sent.** The payload is codes, counts and scores.

---

## 3 · Grounding — the rule that makes the answer usable

```
numbers(answer) ⊆ numbers(context)
```

Every figure in a generated answer is checked against the context it was given. **An answer containing
a figure absent from that context is discarded whole** — not edited, not annotated — and the computed
form is shown instead, with the reason.

⚠️ **The check verifies figures, never the sentence around them.** A model can arrange true numbers
into a misleading claim and the check will pass. `docs/demonstration.md` §4 records exactly that
happening in the first live call. This is a known and accepted limit, not a defect to hide.

---

## 4 · Computed by OptiEDT ≠ Explained by AI

| **Computed by OptiEDT** | **Explained by AI** |
|---|---|
| feasibility · placement · scores · ranking · criteria · dominance · the recommendation and the rule that chose it | natural-language explanation · interpretation · answers to questions · the run report |

On screen:

- Every answer is preceded by an origin label — **`Computed by the application`** or **`Written by the
  language service`** — and the two are visually distinct (`.assistant__origin--generated`).
- ⚠️ **The label goes above the text**, never beside or below it. A reader who reaches the end of a
  paragraph before learning a model wrote it has already read it as fact.
- The recommendation on `/compare` is badged **Computed recommendation** and names its rule, because it
  comes from `analysis/ranking.py` and not from the model.
- The panel's one-line contract says the service *computes no score and decides no ranking* and
  *cannot invent a number*.

### What the interface must never do

- Never present a generated sentence without its origin label.
- Never show a **fabricated confidence score** — the system produces none.
- Never show **invented citations or sources**.
- Never **simulate streaming**. The API returns a whole answer in one response; animating characters
  into place would advertise a capability the system does not have. The waiting state is three pulsing
  dots and a line naming what is being waited for.
- Never let the model appear to have produced a figure, a placement or a ranking.

---

## 5 · Fallback

The computed form is produced by `assistant/computed.py` from the same context. It is **complete** —
every figure, straight from the analysis layer — just not written in prose. It is presented as a normal
answer rather than as a degradation, because that is what it is.

`fallbackReason` is always shown, never swallowed. It can say:

- the service is switched off in configuration;
- the provider failed or timed out;
- ⚠️ **the answer contained figures absent from the context, so it was discarded.** This one matters
  most. A reader who never learns it happened cannot know the service is unreliable on their data, and
  neither can an operator.

---

## 6 · Configuration

| Variable | Effect |
|---|---|
| `OPTIEDT_ASSISTANT_ENABLED` | `false` by default. Everything works with it off |
| `OPTIEDT_ASSISTANT_BASE_URL` | Provider endpoint |
| `OPTIEDT_ASSISTANT_API_KEY` | ⚠️ **Secret. Never commit it; never expose it to the browser** |
| `OPTIEDT_ASSISTANT_MODEL` | Model name |
| `OPTIEDT_ASSISTANT_TIMEOUT_SECONDS` | Default 10; past it the computed form is shown |

The key lives only in the backend environment. The browser holds a bearer token and nothing else.

⚠️ **Restarting matters.** The flag is read at start-up. Changing `.env` without restarting the process
leaves the old value in force — which looked exactly like a broken integration until the stale process
was found and killed by port.

---

## 7 · What is and is not verified

✅ **One live provider call is recorded** in `docs/demonstration.md` §4 (Groq · `llama-3.3-70b-versatile`),
and a second on 2026-08-13 during the release freeze: `generated: true`, `fallbackReason: null`,
1.05 s, figures matching the context.

⚠️ **No test calls a live provider, and none can** (C-21). A model's output is not fixed by a seed.

> **Read a green suite as: the application behaves correctly *around* a language model. Never as: the
> assistant was tested against one.**

What the 19 assistant tests do cover: the off state, the discarded-figure state, the origin labelling,
the grounding verifier, the adapter's HTTP behaviour with `urlopen` intercepted, and that no test
reaches a network.

⚠️ One defect no amount of reading found: the adapter sent no `User-Agent`, so the provider's CDN
refused every request with HTTP 403 and every answer silently fell back to the computed form —
**degraded mode working exactly as specified, which is why nothing failed loudly and four audits saw
nothing.** Fixed 2026-08-07 and pinned by a test that calls no provider.
