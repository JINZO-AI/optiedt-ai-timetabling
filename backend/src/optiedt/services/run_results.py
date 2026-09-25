"""Turning a finished run's result into stored candidate timetables.

Every candidate is evaluated by the independent evaluator before it is stored, and the values
the solver reported are checked against the evaluator's (ADR 0009): a disagreement or a hard
violation in a solver timetable is a defect, recorded on the run and logged as an error.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from optiedt.models import Solution, SolverRun, SolverRunEvent
from optiedt.services.solutions import create_solution

logger = logging.getLogger(__name__)

LOG_LIMIT = 200_000


def _agreement(solution: Solution, tiers: list[dict[str, Any]]) -> list[str]:
    """Problems with the solver's reported tier values against the evaluator's."""
    evaluated = solution.evaluation.get("tiers", [])
    solved = [t for t in tiers if t.get("value") is not None]
    problems = []
    for tier in solved:
        value = evaluated[tier["tier"]]
        if value > tier["value"]:
            problems.append(
                f"tier {tier['tier']}: evaluator {value} is worse than the solver's {tier['value']}"
            )
    if solved and evaluated[solved[-1]["tier"]] != solved[-1]["value"]:
        last = solved[-1]
        problems.append(
            f"tier {last['tier']}: evaluator {evaluated[last['tier']]}, solver {last['value']}"
        )
    if solution.hard_violation_count:
        problems.append(f"{solution.hard_violation_count} hard violation(s)")
    return problems


def store_result(db: Session, run: SolverRun, result: dict[str, Any]) -> None:
    config = run.config
    warnings = list(result.get("warnings", []))
    summary: dict[str, Any] = {}
    if result["kind"] == "relaxation":
        summary = {k: v for k, v in result.items() if k != "log_tail"}
    else:
        origin = "repair" if run.kind == "repair" else "solver"
        stored = []
        for profile in result["profiles"]:
            objectives = profile_objectives(config, profile["code"])
            objective_config: dict[str, Any] = {"objectives": objectives}
            if "stability" in objectives and config.get("reference"):
                objective_config["reference"] = config["reference"]
            solution = create_solution(
                db,
                term_id=run.term_id,
                snapshot_id=run.snapshot_id,
                name=f"{config.get('name', 'Run')} · {profile['name']}",
                origin=origin,
                objective_config=objective_config,
                placements=profile["placements"],
                locked=set(config.get("locked", [])),
                profile_code=profile["code"],
                run_id=run.id,
                parent_id=run.source_solution_id,
                created_by_id=run.requested_by_id,
                evaluation_extra={"solver": {"tier0": result["tier0"], "tiers": profile["tiers"]}},
            )
            problems = _agreement(solution, profile["tiers"])
            if problems:
                logger.error(
                    "solver and evaluator disagree",
                    extra={"run_id": str(run.id), "profile": profile["code"], "problems": problems},
                )
                warnings.append(
                    f"{profile['name']}: the independent check disagrees with the solver ("
                    + "; ".join(problems)
                    + "). Please report this."
                )
            solution.evaluation = {**solution.evaluation, "solver_agrees": not problems}
            stored.append({"code": profile["code"], "solution_id": str(solution.id)})
        summary = {
            "tier0": result["tier0"],
            "profiles": [
                {**entry, "tiers": profile["tiers"]}
                for entry, profile in zip(stored, result["profiles"], strict=True)
            ],
            "model_stats": result.get("model_stats", {}),
            "reproducible": result.get("reproducible", False),
            "wall_seconds": result.get("wall_seconds"),
        }
    summary["warnings"] = warnings
    run.result = summary
    run.log = "\n".join(result.get("log_tail", []))[-LOG_LIMIT:] or None
    run.status = "cancelled" if result.get("cancelled") else "succeeded"
    run.phase = "done"
    run.finished_at = datetime.now(UTC)
    run.lease_expires_at = None
    db.add(
        SolverRunEvent(
            run_id=run.id,
            kind=run.status,
            payload={"solutions": [p["solution_id"] for p in summary.get("profiles", [])]},
        )
    )


def profile_objectives(config: dict[str, Any], code: str) -> dict[str, list[int]]:
    for profile in config.get("profiles", []):
        if profile["code"] == code:
            return {name: [int(t), int(w)] for name, (t, w) in profile["objectives"].items()}
    return {}


def solution_ids(run: SolverRun) -> list[uuid.UUID]:
    return [uuid.UUID(p["solution_id"]) for p in run.result.get("profiles", [])]
