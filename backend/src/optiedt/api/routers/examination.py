"""FR-20 — the examination session.

    Criterion (SRS §3.2, Table 19. FR-20. Examination session), quoted verbatim:
      Input       Examinations, students, rooms, period of the session and
                  supervisors
      Processing  Construction of the model of section 6.8 then solving
      Output      One slot and one or more rooms assigned to each examination

⚠️ **202 and poll, exactly like `POST /runs`.** An examination solve on the
reference instance takes about half a minute, and ADR-005's rule is that no
HTTP request is held open for a solve. The client posts, receives a run id,
and polls `GET /api/examinations/{id}` — the same shape the generation screen
already implements for weekly runs.

⚠️ **This router never imports `optiedt.examination`.** The twelfth import
contract forbids it, for the reason the ninth forbids `api → solver`: a router
that could reach the solver could launch a solve inside a request handler. The
service is asked for, and CP-SAT is never named here.

⚠️ **Person in charge only.** SRS Table 2 gives that actor *"read and write on
all the data"* and limits the administrator to accounts and calendar; C-8
settled that Table 2 wins where the flow prose disagrees. Generating a
timetable — weekly or examination — is the same right, and `POST /runs`
already restricts it the same way.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import ExaminationServiceDep, PersonInChargeDep
from optiedt.api.schemas import ExamPlacementOut, ExamRunOut
from optiedt.services.examinations import ExamRunRecord

router = APIRouter(tags=["examinations"])


def _to_out(record: ExamRunRecord) -> ExamRunOut:
    """One record, rendered. Everything shown is already computed — this layer
    arranges, it does not decide (docs/architecture.md's presentation rule)."""
    session = record.session
    timetable = record.timetable

    placements: list[ExamPlacementOut] = []
    if session is not None and timetable is not None:
        exams = {e.id: e for e in session.examinations}
        slots = {s.index: s for s in session.slots}
        for placement in sorted(timetable.placements, key=lambda p: (p.slot, p.examination)):
            exam = exams[placement.examination]
            slot = slots[placement.slot]
            placements.append(
                ExamPlacementOut(
                    examination=exam.id,
                    course=exam.course,
                    promotion=exam.promotion,
                    supervisor=exam.supervisor,
                    candidate_count=exam.candidate_count,
                    slot=placement.slot,
                    day=slot.day,
                    period_index=slot.period_index,
                    rooms=list(placement.rooms),
                    assigned_capacity=sum(
                        record.room_capacities.get(r, 0) for r in placement.rooms
                    ),
                )
            )

    return ExamRunOut(
        id=record.id,
        state=record.state,
        created_at=record.created_at,
        seed=record.seed,
        deterministic_budget=record.deterministic_budget,
        examination_count=len(session.examinations) if session else 0,
        slot_count=len(session.slots) if session else 0,
        spread_penalty=timetable.spread_penalty if timetable else None,
        proven_optimal=timetable.proven_optimal if timetable else None,
        wall_clock_seconds=timetable.wall_clock_seconds if timetable else None,
        placements=placements,
        error=record.error,
    )


@router.post(
    "/examinations",
    response_model=ExamRunOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate the timetable of an examination session",
)
def start_examination_run(
    service: ExaminationServiceDep,
    _user: PersonInChargeDep,
    seed: int = 42,
    deterministic_budget: float = 30.0,
) -> ExamRunOut:
    """Queue an examination solve and answer immediately with its id.

    ⚠️ **202, not 200**, and the body carries `state = PENDING` rather than a
    timetable. The examinations are DERIVED from the instance (C-23), so this
    endpoint takes no examination payload — only the two parameters that make
    a solve reproducible.
    """
    record, _future = service.start(seed=seed, deterministic_budget=deterministic_budget)
    return _to_out(record)


@router.get(
    "/examinations",
    response_model=list[ExamRunOut],
    summary="Examination runs, newest first",
)
def list_examination_runs(
    service: ExaminationServiceDep,
    _user: PersonInChargeDep,
) -> list[ExamRunOut]:
    return [_to_out(r) for r in service.list()]


@router.get(
    "/examinations/{run_id}",
    response_model=ExamRunOut,
    summary="One examination run, polled",
)
def read_examination_run(
    run_id: str,
    service: ExaminationServiceDep,
    _user: PersonInChargeDep,
) -> ExamRunOut:
    record = service.get(run_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no examination run {run_id}",
        )
    return _to_out(record)
