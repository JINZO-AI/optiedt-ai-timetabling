"""Published ITC-2007 results — transcribed from the archive, with the citation.

`docs/testing-strategy.md` §1 asks for "the distance between the cost obtained
and the best known results", so a reference set is required. **Every figure here
is transcribed from a file inside `data/reference/`**, never from recollection
and never from an outside lookup — the same rule that makes
`data/instance/constraint_catalogue.csv` the authority on weights rather than the
PDFs. A number nobody can trace is worse than no number, because it is quoted
with the same confidence.

**Source**, both tables:
`data/reference/itc2007-cct-master/itc2007-cct-master/docs/latex/itc2007.tex`
— the report bundled with the archive.

- *Confronto I* (its Table 4) — the competition finalists, cited there to
  `http://www.cs.qub.ac.uk/itc2007/winner/finalorder.htm`.
- *Confronto II* (its Table 5) — T. Müller's best without a time limit, cited to
  Müller, T. (2008), *ITC2007 solver description: a hybrid approach*, Annals of
  Operations Research 172, 429-446, doi:10.1007/s10479-009-0644-y — alongside the
  bundled solver's own best.

⚠️ **The archive publishes figures for `comp01`-`comp07` only.** The other
fourteen instances are real and are solved, but there is nothing in the
repository to compare them against, and this module does **not** invent one.
`best_known(name)` returns None for them and the report says "no in-repo
reference" rather than quietly omitting the row — an instance missing from a
results table reads as an instance that failed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class PublishedResult:
    """What the archive records for one instance."""

    finalists: Mapping[str, int]
    """Competition finalists' costs (Confronto I). Names spelled as the source
    spells them."""
    muller_unbounded: int
    """T. Müller's best with no time limit (Confronto II)."""
    bundled_solver_unbounded: int
    """The archive's own simulated-annealing best, no time limit (Confronto II).
    Independently reproduced by `cost.py` from the `.sol` files it ships — see
    `tests/integration/test_itc2007_validation.py`, which is what makes this
    column evidence rather than a claim."""

    @property
    def best(self) -> int:
        """The lowest cost the archive records for this instance, from any
        source. "Best known" is used in that narrow sense throughout, and the
        report says so — the literature has since improved on several of these."""
        return min(*self.finalists.values(), self.muller_unbounded, self.bundled_solver_unbounded)


_FINALIST_NAMES = ("T. Muller", "Lu Hao", "Atzuna et al", "Geiger", "Clark et al")

_PUBLISHED: Mapping[str, PublishedResult] = MappingProxyType(
    {
        name: PublishedResult(
            finalists=MappingProxyType(dict(zip(_FINALIST_NAMES, finalists, strict=True))),
            muller_unbounded=muller,
            bundled_solver_unbounded=bundled,
        )
        for name, finalists, muller, bundled in (
            ("comp01", (5, 5, 5, 5, 10), 5, 5),
            ("comp02", (51, 55, 50, 111, 111), 43, 36),
            ("comp03", (84, 71, 82, 128, 119), 72, 66),
            ("comp04", (37, 43, 35, 72, 72), 35, 37),
            ("comp05", (330, 309, 312, 410, 426), 298, 305),
            ("comp06", (48, 53, 69, 100, 130), 41, 40),
            ("comp07", (20, 28, 42, 57, 110), 14, 14),
        )
    }
)


def published_result(name: str) -> PublishedResult | None:
    return _PUBLISHED.get(name)


def best_known(name: str) -> int | None:
    """The best cost the archive records, or None where it records none."""
    result = _PUBLISHED.get(name)
    return result.best if result is not None else None


def instances_with_published_results() -> tuple[str, ...]:
    return tuple(_PUBLISHED)
