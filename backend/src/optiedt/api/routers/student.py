"""The student's own timetable.

    Right (SRS Table 2, transcribed in docs/domain-model.md and authoritative
    by C-8): the student may *"read the timetable of their group"*.
    The Cahier des Charges adds printing: *"students to consult and print the
    timetable of their group"* — which `features/timetable`'s print stylesheet
    and CSV export already provide (FR-10).

⚠️ **What a student is shown is the PUBLISHED timetable, not a run's
candidates.** A run carries three drafts of every group's week, ranked but not
chosen; publication is the act by which the department says which one people
are to follow (`routers/publications`). Serving drafts here would tell students
to follow a timetable nobody adopted, and would make the first ranking they saw
the one they organised their week around.

⚠️ **Every other timetable endpoint is now closed to this role.** `GET /runs`,
the candidate reads, the comparison and the assistant take
`WorksOnTimetablesDep`, which admits every role except the student. Phase 9's
audit recorded that `GET /runs/{id}` accepted any authenticated caller; that
was harmless while every role worked on timetables, and the student is the role
for which it stopped being so.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import InstanceDep, PublicationStoreDep, RunStoreDep, StudentDep
from optiedt.api.schemas import PlacementOut, StudentTimetableOut
from optiedt.services.runs import candidate_of
from optiedt.services.timetables import placements_for_group

router = APIRouter(tags=["student"])


@router.get(
    "/me/timetable",
    response_model=StudentTimetableOut,
    summary="The published timetable of the signed-in student's group",
)
def read_my_timetable(
    instance: InstanceDep,
    runs: RunStoreDep,
    publications: PublicationStoreDep,
    user: StudentDep,
) -> StudentTimetableOut:
    """The group comes from the ACCOUNT, never from the request.

    ⚠️ The same line `routers/availability` draws for a teacher, and for the
    same reason: a group id in the path would let any student name any group,
    which is the defect Phase 5 moved off the availability grid.

    A student account with no group is refused rather than defaulted — an
    account that cannot say whose timetable it owns has no business being shown
    one, and a default would hand it somebody else's.
    """
    if user.group is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A student account may only read the timetable of its own group",
        )

    group = next((g for g in instance.groups if g.id == user.group), None)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No group {user.group!r} in the instance",
        )

    for publication in publications.all():
        record = runs.get(publication.run)
        candidate = candidate_of(record, publication.candidate) if record else None
        if record is None or candidate is None:
            # The trace is broken, so this publication cannot be shown as one.
            # Skipped rather than half-answered, exactly as `GET /publications`
            # does; the foreign key makes it unreachable through the database.
            continue
        return StudentTimetableOut(
            group=group.id,
            group_label=group.label,
            placements=[
                PlacementOut.of(p) for p in placements_for_group(candidate, instance, group.id)
            ],
            published_at=publication.published_at,
            published_by=publication.user,
            run=publication.run,
            candidate=candidate.id,
        )

    # ⚠️ 200 with an empty timetable, not 404. "Nothing has been published yet"
    # and "you asked for something that does not exist" read completely
    # differently to a student, and only the first is true.
    return StudentTimetableOut(
        group=group.id,
        group_label=group.label,
        placements=[],
        published_at=None,
        published_by=None,
        run=None,
        candidate=None,
    )
