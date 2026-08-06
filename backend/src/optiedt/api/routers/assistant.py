"""FR-22, FR-24, FR-25 — the language service, and its absence.

Every route here returns **200 with text**, whether a model spoke or not. There
is no error path for "the assistant is off", because that is not an error: it
is the default configuration, and invariant 5 says only text disappears.

⚠️ **This module is where the run store meets the assistant, and it is the one
place invariant 4 could be broken by accident.** The router reads the record and
assembles a `RunFacts` — values, never a connection. `.importlinter` forbids
`assistant -> db`, so an attempt to shortcut that fails the build; what it
cannot catch is a router handing over more than it should, which is why
`RunFacts` has exactly the fields it has and no `**kwargs`.

⚠️ **`generated` is on every response and the interface must show it.** A
reader has to be able to tell a sentence a language model wrote from one the
application computed. Dropping that flag would make the two indistinguishable —
and the computed form is the honest one, so the confusion would run in the
direction that flatters the model.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from optiedt.analysis.interfaces import Decomposition
from optiedt.api.deps import (
    AssistantDep,
    CurrentUserDep,
    InstanceDep,
    PublicationStoreDep,
    RunStoreDep,
)
from optiedt.api.schemas import AssistantAnswerOut, AssistantQuestionIn
from optiedt.assistant.interfaces import RunFacts
from optiedt.assistant.service import facts_from_run
from optiedt.domain.entities import CandidateId
from optiedt.domain.enums import ConstraintKind
from optiedt.domain.instance import Instance
from optiedt.services.runs import RunRecord

router = APIRouter(tags=["assistant"], prefix="/assistant")


def _require_run(store: RunStoreDep, run_id: str) -> RunRecord:
    record = store.get(run_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No run {run_id!r}")
    return record


def _facts(
    record: RunRecord,
    instance: Instance,
    published: CandidateId | None = None,
    decomposition: Decomposition | None = None,
) -> RunFacts:
    """The whole of what the assistant may see about this run.

    Criterion NAMES come from the instance catalogue, which is the authority on
    codes and labels (docs/dashboard.md) — not from a constant here, and not
    from the model's own vocabulary.
    """
    return facts_from_run(
        run_id=record.run.id,
        seed=record.run.seed,
        deterministic_budget=record.run.deterministic_budget,
        model_version=record.run.model_version,
        weights=dict(record.weights),
        candidates=record.candidates,
        criterion_names={
            c.code: c.name for c in instance.constraints if c.kind is ConstraintKind.SOFT
        },
        published=published,
        decomposition=decomposition,
    )


@router.get(
    "/runs/{run_id}/candidates/{candidate_id}/explanation",
    response_model=AssistantAnswerOut,
    summary="Explain a candidate's quality — falls back to the computed form",
)
def explain_candidate(
    store: RunStoreDep,
    instance: InstanceDep,
    assistant: AssistantDep,
    _user: CurrentUserDep,
    run_id: str,
    candidate_id: str,
) -> AssistantAnswerOut:
    """FR-22. ⚠️ **200 even when the service is off** — the body is then the
    computed form and `generated` is false. A 503 would make a reader think
    something is broken, when the application is working exactly as specified."""
    record = _require_run(store, run_id)
    answer = assistant.explain_candidate(_facts(record, instance), candidate_id)
    return AssistantAnswerOut.of(answer)


@router.post(
    "/runs/{run_id}/question",
    response_model=AssistantAnswerOut,
    summary="Answer a question about a run — invents no figure",
)
def answer_question(
    store: RunStoreDep,
    instance: InstanceDep,
    assistant: AssistantDep,
    _user: CurrentUserDep,
    run_id: str,
    payload: AssistantQuestionIn,
) -> AssistantAnswerOut:
    """FR-24. A question the context cannot answer gets "I cannot answer" and
    no figure — which is the acceptance criterion, not a shortcoming."""
    record = _require_run(store, run_id)
    answer = assistant.answer_question(_facts(record, instance), payload.question)
    return AssistantAnswerOut.of(answer)


@router.get(
    "/runs/{run_id}/report",
    response_model=AssistantAnswerOut,
    summary="A readable report on a run — falls back to the computed form",
)
def produce_report(
    store: RunStoreDep,
    publications: PublicationStoreDep,
    instance: InstanceDep,
    assistant: AssistantDep,
    _user: CurrentUserDep,
    run_id: str,
) -> AssistantAnswerOut:
    """FR-25, and the one that is cut first under time pressure (PPM §8.3).

    ⚠️ Cutting it means cutting the model's prose, not this route: the computed
    form below is a complete report of the run's own figures, which is why that
    reduction was survivable enough to decide in advance.

    ⚠️ **The published candidate is looked up here, in the router, and passed
    in as a value.** `docs/ai-integration.md`'s context table gives a report
    "the published timetable", and the assistant may not fetch it — invariant 4.
    A report that silently omitted the publication would be describing a run
    while leaving out the one candidate the department actually adopted.
    """
    record = _require_run(store, run_id)
    published = next(
        (p.candidate for p in publications.all() if p.run == run_id),
        None,
    )
    answer = assistant.produce_report(_facts(record, instance, published=published))
    return AssistantAnswerOut.of(answer)
