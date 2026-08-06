"""The grounding check: numbers(answer) ⊆ numbers(context).

If the inclusion does not hold the answer is **discarded** and the computed
form is displayed instead. This is the mechanism invariant 4 rests on, and the
whole reason a language model is admitted into a system whose figures must be
defensible before a department.

⚠️ **Be honest about what it establishes.** It detects a figure the model
invented. It does NOT establish that the rest of the sentence is true. "S3 is
the worst criterion at 0.953" and "S3 is the best criterion at 0.953" pass
identically. No requirement depends on it doing more, and that limit is
precisely why no decision the department must defend rests on this service
(docs/ai-integration.md).

**What it does catch**, which is the failure that matters: a model asked to
explain a score writing a plausible number nobody computed. That is the
hallucination a reader cannot detect by eye, because it looks exactly like the
figures around it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from optiedt.assistant.interfaces import ContextPayload, VerificationOutcome

_NUMBER = re.compile(
    r"""
    (?<![\w.])                              # not mid-identifier, nor the tail of 1.2.3
    -?                                      # a leading minus is part of the number
    (?:
        \d{1,3}(?:[   ]\d{3})+    # grouped: 1 000, 12 345
      | \d+                                 # plain: 4271, 218, 42
    )
    (?:[.,]\d+)?                            # a decimal part, point or comma
    (?![\w])                                # not the head of an identifier
    """,
    re.VERBOSE,
)
r"""⚠️ **The alternation is not tidiness — without it the check had a hole.**

The first draft was `\d{1,3}(?:[ ]\d{3})*`, meaning "up to three digits,
optionally followed by space-grouped triples". On `4271` that matches `427`,
then the trailing `(?![\w])` fails because `1` follows; every shorter attempt
fails the same way, and every later starting position is refused by the leading
`(?<![\w.])`. So **`4271` produced no match at all and passed the grounding
check silently** — as would any ungrouped number above 999.

Found by `tests/acceptance/test_fr22.py::test_an_explanation_inventing_a_figure_
is_discarded`, which fabricated exactly such a figure. A verifier that cannot
see a number cannot reject it, and this one would have reported every answer as
grounded in precisely the range where an invented figure is most plausible —
counts of minutes, of periods, of sessions.
"""

_TOLERANCE = 1e-9
"""Floating-point equality only. NOT a rounding allowance - the context already
carries the rounded forms the interface displays (assistant/context.py), so a
tolerance here would admit figures the screen never shows."""


@dataclass(frozen=True, slots=True)
class DefaultAnswerVerifier:
    """Implements `AnswerVerifier`."""

    def verify(self, answer: str, context: ContextPayload) -> VerificationOutcome:
        permitted = set(context.figures.values())
        # Identifiers frequently contain digits - a run id like `a3f9b201c4d5`,
        # a session id like `S0001`, a criterion code like `S3`. The regex's
        # word boundaries already refuse those, because a digit inside an
        # identifier is not preceded or followed by a word boundary. Codes and
        # ids are checked as STRINGS by the caller if at all; they are not
        # figures and are not what this check is about.
        unverified = tuple(
            value
            for value in _numbers_in(answer)
            if not any(abs(value - allowed) <= _TOLERANCE for allowed in permitted)
        )
        return VerificationOutcome(grounded=not unverified, unverified_numbers=unverified)


def _numbers_in(text: str) -> list[float]:
    """Every numeric token, in order of appearance.

    ⚠️ **A comma is a decimal separator here, not a thousands separator.** The
    interface is in French and a model writing French produces "79,82". Reading
    that as 7982 would make a correctly-grounded answer fail, and reading
    "1 000" as 1 and 0 would do the same - hence the space-grouped form in the
    pattern above. Both were chosen from what the interface actually renders,
    not from a general-purpose number grammar.
    """
    values: list[float] = []
    for match in _NUMBER.finditer(text):
        token = match.group().replace(" ", "").replace(" ", "").replace(",", ".")
        try:
            values.append(float(token))
        except ValueError:  # pragma: no cover - the pattern cannot produce one
            continue
    return values
