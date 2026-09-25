from __future__ import annotations

from optiedt.api.schemas.common import Schema


class IssueOut(Schema):
    severity: str
    code: str
    message: str
    entity_type: str | None
    entity_ids: list[str]
    figures: dict[str, float]


class ValidationOut(Schema):
    snapshot_hash: str
    counts: dict[str, int]
    errors: int
    warnings: int
    data_issues: list[IssueOut]
    feasibility_issues: list[IssueOut]
    elapsed_ms: float
