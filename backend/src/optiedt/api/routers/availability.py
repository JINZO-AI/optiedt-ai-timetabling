"""FR-2 — a teacher declares availability on the weekly grid.

`PUT` replaces the whole declaration rather than patching cells, because a
grid is one statement about a week: a slot the teacher left blank must be able
to clear a generated row that said otherwise. A patch endpoint would make a
`SYNTHETIC` declaration impossible to withdraw.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import AvailabilityStoreDep, CurrentUserDep, InstanceDep
from optiedt.api.schemas import AvailabilityIn, AvailabilityOut
from optiedt.domain.entities import TeacherId, User
from optiedt.domain.enums import UserRole
from optiedt.services.availability import build_declaration, effective_availability

router = APIRouter(tags=["availability"])


def _require_teacher(instance: InstanceDep, teacher_id: TeacherId) -> None:
    if not any(t.id == teacher_id for t in instance.teachers):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No teacher {teacher_id!r}"
        )


def _require_own_grid(user: User, teacher_id: TeacherId) -> None:
    """FR-11's acceptance criterion, enforced here rather than in the client.

    ⚠️ **A TEACHER may only reach their own grid**, and which teacher they are
    comes from the TOKEN. Until Phase 5 it came from the path, which is exactly
    what `api/main.py` warned about from Phase 4 onwards: any caller could name
    any teacher.

    A teacher whose account carries no `teacher` link is refused rather than
    given a default - an account that cannot say whose grid it owns has no
    business editing one.

    403, not 404: the grid exists and the caller may not have it. Hiding that
    would be defensible against an anonymous attacker and is not worth the
    confusion here, where the caller is an authenticated member of the faculty.
    """
    if user.role is not UserRole.TEACHER:
        return
    if user.teacher is None or user.teacher != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A teacher account may only read and write its own availability",
        )


@router.get(
    "/teachers/{teacher_id}/availability",
    response_model=list[AvailabilityOut],
    summary="A teacher's declaration, generated rows included",
)
def read_availability(
    instance: InstanceDep,
    store: AvailabilityStoreDep,
    user: CurrentUserDep,
    teacher_id: TeacherId,
) -> list[AvailabilityOut]:
    _require_teacher(instance, teacher_id)
    _require_own_grid(user, teacher_id)
    rows = effective_availability(instance, store)
    return [AvailabilityOut.of(a) for a in rows if a.teacher == teacher_id]


@router.put(
    "/teachers/{teacher_id}/availability",
    response_model=list[AvailabilityOut],
    summary="Replace a teacher's declaration",
)
def declare_availability(
    instance: InstanceDep,
    store: AvailabilityStoreDep,
    user: CurrentUserDep,
    teacher_id: TeacherId,
    payload: AvailabilityIn,
) -> list[AvailabilityOut]:
    _require_teacher(instance, teacher_id)
    _require_own_grid(user, teacher_id)

    known_slots = {s.index for s in instance.slots}
    unknown = sorted({c.slot for c in payload.cells} - known_slots)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown slot indices: {unknown}",
        )

    # A repeated slot in one payload is a client bug, not a merge to resolve
    # silently: the two entries state different things about one cell.
    counts = Counter(c.slot for c in payload.cells)
    duplicated = sorted(slot for slot, n in counts.items() if n > 1)
    if duplicated:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Slot declared more than once: {duplicated}",
        )

    store.declare(
        teacher_id,
        build_declaration(
            teacher=teacher_id,
            semester=payload.semester,
            cells={c.slot: c.state for c in payload.cells},
        ),
    )
    rows = effective_availability(instance, store)
    return [AvailabilityOut.of(a) for a in rows if a.teacher == teacher_id]
