"""Publishing a timetable, and reading the trace it leaves.

The acceptance criterion this closes is:

    Every published timetable traces back to its run, seed and weights.

`GET /publications` therefore answers with the trace assembled, not with a bare
list of candidate ids: a reader must not have to know to join three endpoints
to establish provenance, because the one who does not know is exactly the one
the criterion protects.

⚠️ **Publishing is the person in charge's right** (SRS Table 2, via C-8), and
it is the one action here with a consequence outside the application — a
published timetable is what teachers and students are told to follow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.api.deps import PersonInChargeDep, PublicationStoreDep, RunStoreDep
from optiedt.api.schemas import PublishedTimetableOut
from optiedt.services.publications import PublishedTimetable, new_publication
from optiedt.services.runs import candidate_of

router = APIRouter(tags=["publications"])


@router.post(
    "/runs/{run_id}/candidates/{candidate_id}/publish",
    response_model=PublishedTimetableOut,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a candidate; returns it with its full trace",
)
def publish(
    runs: RunStoreDep,
    publications: PublicationStoreDep,
    user: PersonInChargeDep,
    run_id: str,
    candidate_id: str,
) -> PublishedTimetableOut:
    record = runs.get(run_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No run {run_id!r}")
    candidate = candidate_of(record, candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No candidate {candidate_id!r}")

    publications.publish(new_publication(candidate.id, record.run.id, user.username))
    return PublishedTimetableOut.of(_trace(record, candidate, publications))


@router.get(
    "/publications",
    response_model=list[PublishedTimetableOut],
    summary="Published timetables, newest first, each with its trace",
)
def list_publications(
    runs: RunStoreDep,
    publications: PublicationStoreDep,
    _user: PersonInChargeDep,
) -> list[PublishedTimetableOut]:
    traced: list[PublishedTimetableOut] = []
    for publication in publications.all():
        record = runs.get(publication.run)
        candidate = candidate_of(record, publication.candidate) if record else None
        if record is None or candidate is None:
            # A publication whose run or candidate is missing cannot be traced,
            # and reporting it WITHOUT the trace would be the exact failure the
            # criterion forbids. Skipped rather than half-answered; the
            # foreign key makes this unreachable through the database store.
            continue
        traced.append(PublishedTimetableOut.of(_trace(record, candidate, publications)))
    return traced


def _trace(record, candidate, publications) -> PublishedTimetable:  # type: ignore[no-untyped-def]
    """Assemble the trace from the run record, never from a stored copy.

    Duplicating the seed and weights onto the publication would create a second
    answer to "what produced this?", free to drift from the first.
    """
    publication = publications.for_candidate(candidate.id)
    assert publication is not None  # written immediately above, or listed from
    return PublishedTimetable(
        publication=publication,
        candidate=candidate,
        seed=record.run.seed,
        weights=dict(record.weights),
        model_version=record.run.model_version,
        deterministic_budget=record.run.deterministic_budget,
    )
