"""The portfolio: one run, several weight profiles, several ranked candidates.

This is the use case that joins the two halves of the system. It is the only
module that legitimately imports both `solver` and `analysis` - the solver
places sessions, the analysis layer scores what came back, and neither may
see the other (docs/architecture.md; backend/.importlinter enforces
`analysis -> solver` as a build failure). `services` is where they meet
because a run IS the use case that needs both.

It writes no placement of its own: every placement in a returned Candidate
came from `Solver.solve`, unmodified (invariant 2, CLAUDE.md).

Four rules taken from docs/constraint-model.md, "Weight profiles and the
portfolio", each of which is easy to get wrong in a way that looks harmless:

1. **The total budget is divided between the profiles**, not given to each.
   `deterministic_budget` on a PortfolioRequest is the budget for the WHOLE
   run; each solve receives `total / len(profiles)`. Handing the full budget
   to every profile would silently triple a run's cost against the < 5 min
   target in docs/status.md.

2. **One seed for the whole portfolio.** Diversity must come from varying the
   objective, never the seed - "two candidates differing only by seed differ
   for no reason anyone can state; two candidates from two profiles differ for
   a reason that is exactly the difference between those profiles." Varying
   the seed here would produce a portfolio nobody can explain, which is the
   one thing the comparison screen exists to avoid.

3. **Solves run one after the other, not concurrently** (docs/architecture.md,
   stage 2). Each solve already uses every worker; running profiles in
   parallel would oversubscribe the machine and, worse, reintroduce exactly
   the race ADR-011 removed.

4. **A candidate identical to one already obtained is not retained** - SRS
   Table 29's "at most 3, duplicates removed". Identity is compared on
   placements, not on score: two profiles can disagree about which timetable
   they prefer and still land on the same one.

⚠️ **Scoring uses ONE weight vector for the whole portfolio**, not each
candidate's own producing profile. The exact-decomposition identity
    score(A) - score(B) = 100 * sum(w_i * (n_i(A) - n_i(B)))
only holds when the same w_i prices both sides, so ranking candidates under
two different profiles' weights would silently break the property the whole
explanation feature rests on. `scoring_weights` is that single vector - the
"weights in force" of docs/scoring-and-explanation.md - and defaults to the
catalogue. A candidate's `profile_name` is provenance, never a scoring input.
See analysis/ranking.py's module docstring.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from optiedt.analysis.criteria import build_criteria
from optiedt.analysis.ranking import DefaultRanker
from optiedt.analysis.scoring import evaluate_candidate
from optiedt.domain.entities import (
    Candidate,
    ConstraintCode,
    Placement,
    RoomId,
    RunId,
    SessionId,
    SlotIndex,
    WeightProfile,
)
from optiedt.domain.enums import ConstraintKind
from optiedt.domain.instance import Instance
from optiedt.solver.interfaces import PortfolioResult, Solver, SolverInput

EMPHASIS = 2.0
"""How hard a favouring profile leans on the criteria it favours.

docs/constraint-model.md says student-favouring "raises S2" and
teacher-favouring "raises S3 and S5" without saying by how much, so this
factor is a choice, recorded here rather than buried in a literal.

Doubling, rather than an additive step, because it is scale-free: it means
the same thing whatever a criterion's catalogue weight happens to be, and it
survives someone editing constraint_catalogue.csv.

⚠️ **This constant is what stands between the portfolio and C-5.** Too small
and the profiles converge on one timetable, duplicate removal drops two of
three, and the "at least three candidates" acceptance test fails for a reason
that looks like a bug in the solver rather than a tuning constant. Too large
and a favouring profile degenerates into single-criterion optimisation whose
candidate nobody would adopt. If the portfolio ever returns fewer than three
distinct candidates on the reference instance, raise this BEFORE concluding
anything about C-5 - and record the measurement in docs/status.md.
"""


@dataclass(frozen=True, slots=True)
class PortfolioRequest:
    """Everything one run needs to produce its portfolio.

    Carries no database handle and no run record: persistence is Phase 5
    (docs/status.md). A caller that wants the result recorded stores what
    comes back.
    """

    instance: Instance
    run: RunId
    seed: int
    deterministic_budget: float
    """The budget for the WHOLE portfolio, divided between the profiles - see
    the module docstring, rule 1. Deterministic time, never wall clock
    (ADR-011)."""

    profiles: tuple[WeightProfile, ...] = ()
    """Empty means `default_profiles(instance)`."""

    scoring_weights: dict[ConstraintCode, float] | None = None
    """The single weight vector every candidate is scored and ranked under.
    None means the catalogue defaults. See the module docstring."""

    locked_placements: frozenset[Placement] = frozenset()
    excluded_slots: frozenset[tuple[SessionId, SlotIndex]] = frozenset()
    excluded_rooms: frozenset[tuple[SessionId, RoomId]] = frozenset()
    """Carried through to every solve unchanged. These are the only three
    things a recommendation may alter (ADR-007), so a regenerated run is this
    same call with one of them different - which is exactly what
    `services/regeneration.py` does with it."""

    candidate_id_prefix: str = "cand"


@dataclass(frozen=True, slots=True)
class PortfolioReport:
    """What a portfolio run produced, and what it discarded.

    Separate from PortfolioResult (solver/interfaces.py, which carries only
    the candidates) so that a duplicate is *observable* rather than silently
    absent. C-5 turns on how often duplicates actually occur, and a mechanism
    that removes them without saying so would hide the evidence needed to
    settle it.
    """

    result: PortfolioResult
    duplicates_removed: tuple[str, ...] = field(default_factory=tuple)
    """Profile names whose timetable was identical to one already obtained."""
    infeasible: bool = False
    """True when the instance admits no timetable at all. The hard constraints
    do not vary between profiles, so this is a property of the instance, not
    of any one profile - see generate_portfolio()."""
    deterministic_time_used: float = 0.0
    wall_clock_seconds: float = 0.0


def catalogue_weights(instance: Instance) -> dict[ConstraintCode, float]:
    """The soft-criterion default weights, read from the instance catalogue.

    `data/instance/constraint_catalogue.csv` is the authority on codes, names
    and default weights - not the PDFs and not a constant in this file
    (docs/dashboard.md).
    """
    return {c.code: c.default_weight for c in instance.constraints if c.kind is ConstraintKind.SOFT}


def profiles_from(base: dict[ConstraintCode, float]) -> tuple[WeightProfile, ...]:
    """The three profiles of docs/constraint-model.md, over a supplied base.

    balanced = the base as given · student-favouring raises S2 · teacher-
    favouring raises **S3 and S4**. Returned in a fixed order so a run is
    reproducible (ADR-011); a set or a dict comprehension over an unordered
    source would not be.

    ⚠️ **Teacher-favouring raised S3 and S5 until 2026-08-07, and raising S5
    was the whole of C-15.** S5 is an admitted PROXY - C-12 records it as "a
    labeled stand-in for real preference data, not a definition of teacher
    preference", because `teacher_availability.csv` has no preferred-window
    column and S5 therefore counts sessions at the edge of the day. Spending a
    teacher profile's largest weight on a proxy for absent data is not
    favouring teachers, and it measurably was not: teacher-favouring came back
    **worst of the three on S3, S4 AND S5 at once**, and on the overall score.

    S3 and S4 are what measure teacher experience from real placements, and
    C-4 chose *teacher* as S4's resource for exactly that reason - "S3 already
    penalises gaps within a day a teacher is present, but not a teacher spread
    thinly across many low-load days - S4 fills exactly that gap."

    Measured on the reference instance, seed 42, budget 90 (C-15):

        raises S3, S5   ->  S3=29  S4=65  S5=103  score 79.45   (won nothing)
        raises S3, S4   ->  S3= 0  S4=69  S5= 95  score 81.10   (best S3 AND S5)

    S3=0 is the proven single-criterion optimum, reached in 14.45 of 90 budget
    units when S3 is solved alone.

    ⚠️ **A favouring profile promises the best value of its HEADLINE criterion
    among the three, not a win on every criterion of its constituency** - the
    stronger reading is unachievable at any weighting and claiming it is what
    made C-15 look like a defect. Proof that it is unachievable rather than
    merely unachieved: solving S3 alone drives S5 to 113; solving S5 alone
    drives S4 to 73. The teacher criteria genuinely conflict. `balanced` still
    holds the best S4, and that is multi-objective reality, not a regression.

    The base is the catalogue for an ordinary run. It is the run's ADJUSTED
    weight vector for a run regenerated from an accepted `weight_delta`
    (FR-23), so the delta steers the SEARCH and not only the scoring - a
    recommendation that changed the score of an unchanged timetable would be
    a recommendation about nothing.
    """

    def raising(*codes: ConstraintCode) -> dict[ConstraintCode, float]:
        return {
            code: (weight * EMPHASIS if code in codes else weight) for code, weight in base.items()
        }

    return (
        WeightProfile(name="balanced", weights=dict(base)),
        WeightProfile(name="student-favouring", weights=raising("S2")),
        WeightProfile(name="teacher-favouring", weights=raising("S3", "S4")),
    )


def default_profiles(instance: Instance) -> tuple[WeightProfile, ...]:
    """The three profiles over the catalogue's own default weights."""
    return profiles_from(catalogue_weights(instance))


def placement_signature(placements: tuple[Placement, ...]) -> tuple[tuple[str, int, str], ...]:
    """A canonical, order-independent identity for a timetable.

    Sorted, because two solves may return the same assignment in a different
    order and they are the same timetable. Compared on (session, slot, room)
    only - a Candidate's score and profile_name are about how it was obtained,
    not about what it IS, and including them would defeat duplicate removal
    exactly when it matters (two profiles agreeing on one timetable).
    """
    return tuple(sorted((p.session, p.slot, p.room) for p in placements))


def generate_portfolio(request: PortfolioRequest, solver: Solver) -> PortfolioReport:
    """Solve once per profile, score, deduplicate and rank.

    Stops at the first infeasible solve rather than trying the rest: H1-H12
    are declared identically whatever the weights, so an instance that admits
    no timetable under one profile admits none under any. Continuing would
    burn the remaining budget to learn nothing. The caller enters the
    diagnosis run (stage 3, Phase 5) on `report.infeasible`; this module does
    not call `diagnose()` itself, which is why PortfolioResult.diagnosis is
    left None here.
    """
    profiles = request.profiles or default_profiles(request.instance)
    weights = (
        request.scoring_weights
        if request.scoring_weights is not None
        else catalogue_weights(request.instance)
    )
    criteria = build_criteria(request.instance)
    per_profile_budget = request.deterministic_budget / len(profiles)

    candidates: list[Candidate] = []
    seen: set[tuple[tuple[str, int, str], ...]] = set()
    duplicates: list[str] = []
    deterministic_used = 0.0
    wall_clock = 0.0

    for index, profile in enumerate(profiles):
        output = solver.solve(
            SolverInput(
                instance=request.instance,
                profile=profile,
                seed=request.seed,
                deterministic_budget=per_profile_budget,
                locked_placements=request.locked_placements,
                excluded_slots=request.excluded_slots,
                excluded_rooms=request.excluded_rooms,
            )
        )
        deterministic_used += output.deterministic_time_used
        wall_clock += output.wall_clock_seconds

        if output.infeasible:
            return PortfolioReport(
                result=PortfolioResult(candidates=()),
                duplicates_removed=tuple(duplicates),
                infeasible=True,
                deterministic_time_used=deterministic_used,
                wall_clock_seconds=wall_clock,
            )

        signature = placement_signature(output.placements)
        if signature in seen:
            duplicates.append(profile.name)
            continue
        seen.add(signature)

        candidates.append(
            evaluate_candidate(
                candidate_id=f"{request.candidate_id_prefix}-{index + 1}",
                run=request.run,
                profile_name=profile.name,
                placements=output.placements,
                cost=output.cost,
                criteria=criteria,
                instance=request.instance,
                weights=weights,
            )
        )

    ranked = DefaultRanker(weights=weights).rank(candidates)
    return PortfolioReport(
        result=PortfolioResult(candidates=tuple(ranked)),
        duplicates_removed=tuple(duplicates),
        infeasible=False,
        deterministic_time_used=deterministic_used,
        wall_clock_seconds=wall_clock,
    )
