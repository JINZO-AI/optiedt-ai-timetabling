"""The validation report shown before scheduling: data-quality checks and pre-checks."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from optiedt.problem.data_checks import check_data
from optiedt.problem.issues import Issue
from optiedt.problem.model import build_problem
from optiedt.problem.snapshot import content_hash
from optiedt.security.permissions import Permission, Principal
from optiedt.services.snapshots import compile_snapshot
from optiedt.solver.domains import build_context
from optiedt.solver.precheck import precheck


@dataclass(frozen=True, slots=True)
class ValidationReport:
    snapshot_hash: str
    counts: dict[str, int]
    data_issues: list[Issue]
    feasibility_issues: list[Issue]
    elapsed_ms: float

    @property
    def errors(self) -> int:
        return sum(1 for i in self.data_issues + self.feasibility_issues if i.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.data_issues + self.feasibility_issues if i.severity == "warning")


def build_report(db: Session, principal: Principal, term_id: uuid.UUID) -> ValidationReport:
    principal.require(Permission.TERM_DATA_READ)
    started = time.perf_counter()
    snapshot = compile_snapshot(db, term_id)
    problem = build_problem(snapshot)
    data_issues = check_data(problem)
    feasibility: list[Issue] = []
    if not any(i.code == "too_many_atoms" for i in data_issues):
        feasibility = precheck(build_context(problem))
    return ValidationReport(
        snapshot_hash=content_hash(snapshot.model_dump(mode="json")),
        counts={
            "activities": len(problem.activities),
            "sessions": len(problem.sessions),
            "periods_to_place": sum(s.duration for s in problem.sessions),
            "rooms": len(problem.rooms),
            "instructors": len(problem.instructors),
            "groups": len(problem.groups),
            "rules": len(problem.rules),
            "open_slots": len(problem.open_slots),
        },
        data_issues=data_issues,
        feasibility_issues=feasibility,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
    )
