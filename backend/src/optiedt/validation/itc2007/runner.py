"""Solve → evaluate independently → compare with the archive → report.

The two questions `docs/testing-strategy.md` §1 asks, in order:

1. **Does any timetable produced violate a hard constraint?** Answered by
   `cost.py` re-derived from the placements, never by CP-SAT's own status. A
   solver that reports OPTIMAL on a model with a missing constraint is exactly as
   confident as one that does not.
2. **How far is the cost from the best known results?** Answered against
   `published.py`, whose every figure is traceable to a file in the archive.

`python -m optiedt.validation.itc2007` runs it; `scripts/validate-itc2007.ps1`
wraps that with the archive check.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

from optiedt.validation.itc2007.cost import Evaluation, evaluate
from optiedt.validation.itc2007.model import SolveConfig, SolveReport, solve
from optiedt.validation.itc2007.problem import Itc2007Instance
from optiedt.validation.itc2007.published import best_known
from optiedt.validation.itc2007.reader import (
    archives_present,
    competition_instance_names,
    instance_path,
    read_instance,
)


@dataclass(frozen=True, slots=True)
class InstanceResult:
    """One instance, solved and judged."""

    name: str
    evaluation: Evaluation | None
    """None when no timetable was produced at all — see ``report``."""
    report: SolveReport
    elapsed_seconds: float

    @property
    def solved(self) -> bool:
        return self.evaluation is not None

    @property
    def feasible(self) -> bool:
        return self.evaluation is not None and self.evaluation.hard.feasible

    @property
    def cost(self) -> int | None:
        return self.evaluation.soft.total if self.evaluation is not None else None

    @property
    def encoding_matches_cost(self) -> bool:
        """The model's own soft costs must equal the independently recomputed
        ones, component by component.

        This is the real cross-check — the same guard, for the same reason, as
        the product's `tests/integration/test_objective_matches_analysis.py`.
        It reads the values back from the auxiliaries CP-SAT assigned, so it
        tests the *encoding*: if `model.py` and `cost.py` ever disagree about
        what ITC-2007's rules say, one of the four components moves and says so.
        """
        breakdown = self.report.objective_breakdown
        return (
            self.evaluation is not None
            and breakdown is not None
            and breakdown == self.evaluation.soft
        )

    @property
    def objective_value_matches(self) -> bool:
        """Whether ``CpSolver.objective_value`` agrees with the solution returned.

        ⚠️ **It sometimes does not, under `interleave_search`.** Measured
        2026-07-31 on comp02/comp18/comp21: the objective was reported 5 to 15
        above the value of the objective expression evaluated at the very
        solution the solver handed back, on solves that stopped on the budget
        without proving optimality. With `interleave_search = false` the two
        agree exactly on the same instances. The parameter is marked
        Experimental upstream.

        **Nothing reported by this harness depends on it**: validity and cost
        both come from `cost.py`, re-derived from the placements. It is
        surfaced because a silent discrepancy between a solver's own headline
        number and its answer is worth knowing about — and because the product
        makes the same call (`SolverOutput.cost`), where the same reasoning
        applies for the same reason.
        """
        return self.evaluation is not None and self.report.objective == self.evaluation.soft.total

    @property
    def gap(self) -> int | None:
        """Cost minus the best the archive records. None where it records none."""
        reference = best_known(self.name)
        if reference is None or self.cost is None:
            return None
        return self.cost - reference

    @property
    def gap_percent(self) -> float | None:
        reference = best_known(self.name)
        gap = self.gap
        if reference is None or gap is None:
            return None
        if reference == 0:
            return 0.0 if gap == 0 else float("inf")
        return 100.0 * gap / reference


def run_instance(instance: Itc2007Instance, config: SolveConfig) -> InstanceResult:
    started = time.perf_counter()
    report = solve(instance, config)
    elapsed = time.perf_counter() - started
    evaluation = (
        None if report.infeasible or not report.solution else evaluate(instance, report.solution)
    )
    return InstanceResult(
        name=instance.name,
        evaluation=evaluation,
        report=report,
        elapsed_seconds=elapsed,
    )


def run(names: tuple[str, ...], config: SolveConfig) -> list[InstanceResult]:
    """Solve each instance in turn, reporting progress to stderr.

    Sequential, and progress goes to stderr, because a 21-instance sweep runs
    for tens of minutes: a run that prints nothing until the end is
    indistinguishable from a hung one, and the last session lost hours to
    exactly that ambiguity (C-13).
    """
    results: list[InstanceResult] = []
    for position, name in enumerate(names, start=1):
        print(f"[{position}/{len(names)}] {name} ...", end="", file=sys.stderr, flush=True)
        instance = read_instance(instance_path(name))
        # The `.ctt` Name: field is the faculty's own label ("Fis0506-1"), not
        # the file name the archive and every published table use.
        result = run_instance(
            Itc2007Instance(
                name=name,
                days=instance.days,
                periods_per_day=instance.periods_per_day,
                courses=instance.courses,
                rooms=instance.rooms,
                curricula=instance.curricula,
                unavailable=instance.unavailable,
            ),
            config,
        )
        results.append(result)
        print(
            f" cost {result.cost if result.cost is not None else 'none'}"
            f", hard {result.evaluation.hard.total if result.evaluation else '-'}"
            f", {result.elapsed_seconds:.0f}s",
            file=sys.stderr,
            flush=True,
        )
    return results


def format_report(results: list[InstanceResult], config: SolveConfig) -> str:
    lines: list[str] = []
    lines.append("ITC-2007 Track 3 (curriculum-based course timetabling)")
    lines.append(
        f"seed {config.seed} - deterministic budget {config.deterministic_budget:g} per instance "
        f"- workers {config.workers or 'all'} - interleave_search on (ADR-011)"
    )
    lines.append("")
    header = (
        f"{'instance':9s} {'hard':>5s} {'cost':>6s} {'rc':>5s} {'mwd':>5s} {'cc':>5s} "
        f"{'rs':>4s} {'best':>6s} {'gap':>6s} {'gap%':>7s} {'opt':>4s} {'wall':>7s}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for result in results:
        reference = best_known(result.name)
        if result.evaluation is None:
            state = "INFEASIBLE" if result.report.infeasible else "NO SOLUTION"
            lines.append(f"{result.name:9s} {state}")
            continue
        soft = result.evaluation.soft
        gap = result.gap
        gap_pct = result.gap_percent
        lines.append(
            f"{result.name:9s} "
            f"{result.evaluation.hard.total:5d} "
            f"{soft.total:6d} "
            f"{soft.room_capacity:5d} {soft.min_working_days:5d} "
            f"{soft.curriculum_compactness:5d} {soft.room_stability:4d} "
            f"{(str(reference) if reference is not None else '-'):>6s} "
            f"{(f'{gap:+d}' if gap is not None else '-'):>6s} "
            f"{(f'{gap_pct:.0f}%' if gap_pct is not None else '-'):>7s} "
            f"{('yes' if result.report.proven_optimal else 'no'):>4s} "
            f"{result.elapsed_seconds:6.1f}s"
        )

    lines.append("")
    valid = [r for r in results if r.feasible]
    produced = [r for r in results if r.solved]
    lines.append(
        f"Hard constraints: {len(valid)} of {len(results)} timetables violate none "
        "(re-derived from the instance, not taken from the solver's status)."
    )
    drifted = [r.name for r in produced if not r.encoding_matches_cost]
    lines.append(
        "Encoding: the model's own soft costs equal the recomputed ones on every "
        "instance, component by component."
        if not drifted
        else f"❌ ENCODING DRIFT — model.py and cost.py disagree on: {', '.join(drifted)}"
    )
    reporting = [r.name for r in produced if not r.objective_value_matches]
    if reporting:
        lines.append(
            f"⚠️ CpSolver.objective_value disagreed with the solution returned on "
            f"{len(reporting)} instance(s): {', '.join(reporting)}. Known behaviour of "
            "`interleave_search` on solves that stop before proving optimality — the "
            "encoding above is unaffected, and every figure here is re-derived from the "
            "placements. See ADR-011."
        )
    compared = [r for r in valid if r.gap is not None]
    if compared:
        gaps = [r.gap_percent for r in compared if r.gap_percent is not None]
        lines.append(
            f"Compared with the archive's published results on {len(compared)} instances: "
            f"gap {min(gaps):.0f}%-{max(gaps):.0f}%, median {sorted(gaps)[len(gaps) // 2]:.0f}%."
        )
    lines.append(
        f"{len(results) - len(compared)} instances have no published figure in "
        "data/reference/ and are reported on validity alone (see published.py)."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m optiedt.validation.itc2007",
        description="Validate the modelling approach on the published ITC-2007 Track 3 instances.",
    )
    defaults = SolveConfig()
    parser.add_argument("names", nargs="*", help="instances to run (default: comp01..comp21)")
    parser.add_argument("--budget", type=float, default=defaults.deterministic_budget)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    parser.add_argument("--workers", type=int, default=defaults.workers)
    arguments = parser.parse_args(argv)

    if not archives_present():
        print(
            "data/reference/ holds no ITC-2007 archive - it is gitignored and not part of\n"
            "the repository. Run scripts/check-reference-data.ps1 for what is expected.",
            file=sys.stderr,
        )
        return 2

    config = SolveConfig(
        seed=arguments.seed,
        deterministic_budget=arguments.budget,
        workers=arguments.workers,
    )
    names = tuple(arguments.names) or competition_instance_names()
    results = run(names, config)
    print(format_report(results, config))

    unusable = [r.name for r in results if not r.feasible]
    if unusable:
        print(f"\nFAILED - hard constraints violated or no timetable: {', '.join(unusable)}")
        return 1

    # Encoding drift fails the run too, and arguably harder: an invalid
    # timetable is visibly wrong, whereas model.py and cost.py disagreeing
    # means every cost printed above is unreliable while looking fine.
    drifted = [r.name for r in results if r.solved and not r.encoding_matches_cost]
    if drifted:
        print(f"\nFAILED - model.py and cost.py disagree on: {', '.join(drifted)}")
        return 1
    return 0
