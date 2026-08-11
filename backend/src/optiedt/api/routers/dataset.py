"""FR-1 — the person in charge loads and manages the department's data.

    Criterion (SRS §3.2, Table 4. FR-1. Data management), quoted verbatim:
      Input       Files or forms validated by the server
      Processing  Verification of the types and of the references, then
                  recording
      Output      Entities recorded and report of the rejected lines

⚠️ **The person in charge, not the administrator.** SRS Table 2 gives the person
in charge *"read and write on all the data"* and limits the administrator to
*"management of the accounts and of the calendar"*. CdC §4.3 and SRS §3.3 both
say the administrator loads the data; **C-8 settled that Table 2 wins where the
flow prose disagrees**, and `domain/enums.UserRole` already records the ruling.

⚠️ **The order of operations in `import_dataset` is the atomicity guarantee**,
and it is the only place it exists: validate, then check compatibility, then
write. Nothing before the last step touches a store, so a refused import has
nothing to roll back — there is no transaction to abort because none was
opened. The write itself is one row of one store in one transaction
(`db/repositories.SqlDatasetStore.save`).

⚠️ **Withdrawal is a base replacement and takes the same check** (A7,
refinement 9). `DELETE /api/dataset` restores the reference files, which can
orphan a declaration or a closure exactly as an import can — a teacher the
imported dataset added does not exist in `data/instance/`. Skipping the check
here would leave a hole the size of the undo button.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, status

from optiedt.api.deps import (
    AvailabilityStoreDep,
    CalendarStoreDep,
    DatasetStoreDep,
    PersonInChargeDep,
    base_instance,
    get_instance,
)
from optiedt.api.schemas import (
    DatasetImportOut,
    DatasetSummaryOut,
    IncompatibilityOut,
    RejectedLineOut,
)
from optiedt.instance.validation import RejectedLine, validate_dataset
from optiedt.services.dataset import DatasetStore, Incompatibility, check_compatibility

router = APIRouter(tags=["dataset"])

MAX_FILE_BYTES = 4 * 1024 * 1024
"""A department dataset is tens of kilobytes; the reference one is 36 KB.

Bounded because these files are read whole into memory and stored in one row.
Refusing at the edge is cheaper than discovering the limit as a failed
transaction, and 4 MB is two orders of magnitude above anything plausible.
"""


@router.get(
    "/dataset",
    response_model=DatasetSummaryOut,
    summary="The department data in force, and where it came from",
)
def read_dataset(
    store: DatasetStoreDep,
    _user: PersonInChargeDep,
) -> DatasetSummaryOut:
    """⚠️ Person in charge only — SRS Table 2 gives that actor all the data.

    Every other role reads the *content* through `GET /instance`, which serves
    whichever dataset is in force. What is restricted here is the provenance:
    who replaced the department's data and when.
    """
    return DatasetSummaryOut.of(base_instance(), store.current())


@router.post(
    "/dataset",
    response_model=DatasetImportOut,
    summary="Replace the department data from a set of files",
)
async def import_dataset(
    store: DatasetStoreDep,
    availability: AvailabilityStoreDep,
    calendar: CalendarStoreDep,
    user: PersonInChargeDep,
    files: list[UploadFile],
) -> DatasetImportOut:
    """Verify a supplied dataset, then record it — or record nothing and report.

    Answers **200** in both cases, with `accepted` saying which happened. A
    refused import is not a malformed request: the client sent exactly what this
    endpoint is for, and the report *is* the response body. A 4xx carrying the
    same payload would make every client treat the report as an error to log
    rather than as a result to display.
    """
    supplied, oversize, undecodable = await _read(files)
    if oversize:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file(s) above {MAX_FILE_BYTES} bytes: {', '.join(oversize)}",
        )

    # The catalogue comes from the application's own files and can never come
    # from an upload — ADR-003, invariant 7. `validate_dataset` has no other way
    # to fill `Instance.constraints`.
    result = validate_dataset(supplied, get_instance().constraints)
    if undecodable or result.instance is None:
        return _outcome(
            store,
            rejected=(*undecodable, *result.rejected),
            references_checked=result.references_checked,
        )

    found = check_compatibility(result.instance, availability, calendar)
    if found:
        return _outcome(store, incompatibilities=found)

    store.save(supplied, author=user.username)
    return _outcome(store)


@router.delete(
    "/dataset",
    response_model=DatasetImportOut,
    summary="Withdraw the imported dataset; the reference files govern again",
)
def withdraw_dataset(
    store: DatasetStoreDep,
    availability: AvailabilityStoreDep,
    calendar: CalendarStoreDep,
    _user: PersonInChargeDep,
) -> DatasetImportOut:
    """The withdrawal the layering exists for — and it is checked like an import.

    ⚠️ It restores `data/instance/` as loaded, not "the previous import". There
    is one dataset, and removing it leaves the reference files in force, which
    is the only state this application can restore without keeping a history
    nobody asked for — the same rule `DELETE /api/calendar` follows.
    """
    if store.current() is None:
        return _outcome(store)

    found = check_compatibility(get_instance(), availability, calendar)
    if found:
        return _outcome(store, incompatibilities=found)

    store.reset()
    return _outcome(store)


async def _read(
    files: list[UploadFile],
) -> tuple[dict[str, str], list[str], tuple[RejectedLine, ...]]:
    """Uploads as text, keyed by filename. Undecodable bytes are not a crash.

    ⚠️ A file that is not UTF-8 becomes a **rejected line** rather than an
    exception: "this is not a text file" is exactly what FR-1's report exists to
    say, and a 500 would say it as a defect of the server. It is kept out of the
    supplied set so the validator also reports it as missing, which is what it
    is — nothing usable arrived under that name.
    """
    supplied: dict[str, str] = {}
    oversize: list[str] = []
    undecodable: list[RejectedLine] = []
    for upload in files:
        name = (upload.filename or "").strip() or "(unnamed)"
        raw = await upload.read()
        if len(raw) > MAX_FILE_BYTES:
            oversize.append(name)
            continue
        try:
            supplied[name] = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            undecodable.append(
                RejectedLine(
                    file=name,
                    line=None,
                    reason="the file is not readable as UTF-8 text; a CSV file is expected",
                )
            )
    return supplied, oversize, tuple(undecodable)


def _outcome(
    store: DatasetStore,
    rejected: tuple[RejectedLine, ...] = (),
    incompatibilities: tuple[Incompatibility, ...] = (),
    references_checked: bool = True,
) -> DatasetImportOut:
    """The response, always describing the dataset that is ACTUALLY in force.

    ⚠️ Built after the decision, from the store, rather than from what was
    supplied. On a refused import that is the previous dataset — which is the
    whole of *"the existing dataset remains active when compatibility validation
    fails"*, stated in the response body rather than only in a document.
    """
    return DatasetImportOut(
        accepted=not rejected and not incompatibilities,
        dataset=DatasetSummaryOut.of(base_instance(), store.current()),
        rejected_lines=[RejectedLineOut.of(r) for r in rejected],
        incompatibilities=[IncompatibilityOut.of(i) for i in incompatibilities],
        references_checked=references_checked,
    )
