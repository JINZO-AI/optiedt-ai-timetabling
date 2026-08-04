"""FR-19 — the run record, against real PostgreSQL.

**One suite, run twice: once against the in-memory store and once against the
database.** That is the point of the Protocols Phase 4 left behind. Two
implementations of one contract drift silently unless something runs the same
assertions over both, and the failure mode is nasty here — the in-memory store
is what every other test uses, so a divergence would only surface in
production, after a restart, as a run that came back subtly different from the
one that was written.

⚠️ **Against PostgreSQL, not SQLite.** The repository ships `postgres:17-alpine`
(`docker-compose.yml`) and configures alembic and `psycopg` for it; SQLite
appears nowhere in the design, and its only trace is two lines inherited from
GitHub's Python `.gitignore` template. Testing against an engine the project
does not ship would prove the wrong thing about DDL, type affinity and
sequences.

**A dedicated database, not the developer's.** These tests create and truncate
tables, and on 2026-08-04 an unrelated API test wrote into the development
database because it did not override its store. `optiedt_test` is created on
demand beside it, so nothing here can touch a real run.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from optiedt.core.config import Settings
from optiedt.domain.entities import Candidate, DiagnosisResult, Placement, SubScore
from optiedt.domain.enums import AvailabilityState, DeclarationSource, RunState
from optiedt.preanalysis.checks import CheckResult
from optiedt.services.availability import InMemoryAvailabilityStore, build_declaration
from optiedt.services.publications import InMemoryPublicationStore, new_publication
from optiedt.services.runs import InMemoryRunStore, RunRequest, RunStore, new_run_record

pytestmark = pytest.mark.database

TEST_DATABASE = "optiedt_test"
REQUEST = RunRequest(seed=42, deterministic_budget=90.0)
WEIGHTS = {"S2": 0.25, "S3": 0.15}


def _test_database_url() -> str:
    """The configured server, with a database of this suite's own."""
    configured = os.environ.get("OPTIEDT_TEST_DATABASE_URL")
    if configured:
        return configured
    base = Settings().database_url
    return base.rsplit("/", 1)[0] + "/" + TEST_DATABASE


@pytest.fixture(scope="session")
def session_factory() -> Iterator[sessionmaker[Session]]:
    """A live PostgreSQL, or skip with a message that names the fix.

    Skipping rather than failing is decided in `scripts/run-checks.ps1`, which
    knows whether Docker is running: a forgotten `docker compose up -d` fails
    the build there, while a machine with no Docker at all skips. Here, the
    only honest thing to do without a server is to say so.
    """
    from optiedt.db import models  # noqa: F401 - registers the tables on Base.metadata
    from optiedt.db.base import Base
    from optiedt.db.session import get_engine

    # ⚠️ That import is load-bearing, not tidiness. `Base.metadata` is empty
    # until the model module is imported, so `create_all` below silently
    # creates NOTHING and every test fails with "relation runs does not
    # exist". `migrations/env.py` carries the same import for the same reason -
    # there, a partial metadata makes autogenerate emit DROP statements.

    url = _test_database_url()
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    try:
        # ⚠️ A SHORT timeout, and the fixture is session-scoped so the answer is
        # reached once. Without both, a stopped container cost 4.5 MINUTES of
        # connection timeouts to arrive at "skipped" - measured 2026-08-04 when
        # Docker restarted mid-session. A skip that takes longer than the tests
        # teaches people to stop running them.
        admin = sqlalchemy.create_engine(
            admin_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 3}
        )
        with admin.connect() as conn:
            exists = conn.execute(
                text("select 1 from pg_database where datname = :name"), {"name": TEST_DATABASE}
            ).scalar()
            if not exists:
                conn.execute(text(f'create database "{TEST_DATABASE}"'))
        admin.dispose()
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.DBAPIError) as exc:  # pragma: no cover
        pytest.skip(
            f"PostgreSQL is not reachable at {admin_url}: {exc}. "
            "Start it with `docker compose up -d`, and check OPTIEDT_POSTGRES_PORT "
            "if another server already owns 5432."
        )

    engine = get_engine(url)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture(autouse=True)
def clean(session_factory: sessionmaker[Session]) -> None:
    """Every test starts from an empty database.

    TRUNCATE ... CASCADE rather than dropping the schema: it is far faster, and
    it exercises the foreign keys the migration actually created.
    """
    with session_factory() as session, session.begin():
        session.execute(
            text("truncate runs, availability_declarations, publications restart identity cascade")
        )


@pytest.fixture(params=["memory", "database"])
def run_store(request: pytest.FixtureRequest, session_factory: sessionmaker[Session]) -> RunStore:
    if request.param == "memory":
        return InMemoryRunStore()
    from optiedt.db.repositories import SqlRunStore

    return SqlRunStore(session_factory)


@pytest.fixture(params=["memory", "database"])
def publication_store(request: pytest.FixtureRequest, session_factory: sessionmaker[Session]):
    if request.param == "memory":
        return InMemoryPublicationStore()
    from optiedt.db.repositories import SqlPublicationStore

    return SqlPublicationStore(session_factory)


@pytest.fixture(params=["memory", "database"])
def availability_store(request: pytest.FixtureRequest, session_factory: sessionmaker[Session]):
    if request.param == "memory":
        return InMemoryAvailabilityStore()
    from optiedt.db.repositories import SqlAvailabilityStore

    return SqlAvailabilityStore(session_factory)


def candidate(cid: str, score: float, slot: int = 0) -> Candidate:
    return Candidate(
        id=cid,
        run="r1",
        profile_name="balanced",
        cost=7,
        score=score,
        placements=(Placement(session="s1", slot=slot, room="R1"),),
        sub_scores=(SubScore(criterion="S2", raw_value=3.0, normalised=0.75),),
    )


# ── the run record ─────────────────────────────────────────────────────


def test_a_run_survives_a_round_trip_intact(run_store: RunStore) -> None:
    """Everything FR-19 names: the data, the seed, the weights, the results."""
    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)

    read = run_store.get("r1")
    assert read is not None
    assert read.run.id == "r1"
    assert read.run.seed == 42
    assert read.run.deterministic_budget == 90.0
    assert read.run.model_version == record.run.model_version
    assert read.weights == WEIGHTS
    assert read.state is RunState.PENDING


def test_created_at_survives_with_its_timezone(run_store: RunStore) -> None:
    """A naive datetime read back would silently shift a run by hours.

    The column is `DateTime(timezone=True)` for this reason; PostgreSQL would
    otherwise return a naive value and every comparison against `datetime.now(UTC)`
    would be wrong by the machine's offset.
    """
    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)

    read = run_store.get("r1")
    assert read is not None
    assert read.run.created_at.tzinfo is not None
    assert abs((read.run.created_at - record.run.created_at).total_seconds()) < 1


def test_an_unknown_run_is_none_and_a_duplicate_is_refused(run_store: RunStore) -> None:
    assert run_store.get("missing") is None
    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    with pytest.raises(KeyError):
        run_store.create(record)


def test_saving_advances_the_state_and_the_timings(run_store: RunStore) -> None:
    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    run_store.save(record.to(RunState.PREANALYSIS))

    read = run_store.get("r1")
    assert read is not None
    assert read.state is RunState.PREANALYSIS


def test_the_five_checks_are_recorded_in_order(run_store: RunStore) -> None:
    """FR-12's report has to survive a restart, in the order it was reported."""
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    checks = tuple(
        CheckResult(name=name, passed=True, detail=f"detail {name}")
        for name in ("ROOM_SUITABILITY", "SLOT_COVERAGE", "TEACHER_LOAD")
    )
    run_store.save(dataclasses.replace(record.to(RunState.PREANALYSIS), pre_analysis=checks))

    read = run_store.get("r1")
    assert read is not None
    assert [c.name for c in read.pre_analysis] == [c.name for c in checks]
    assert read.pre_analysis[1].detail == "detail SLOT_COVERAGE"


def test_a_failing_check_keeps_its_resource_and_quantity(run_store: RunStore) -> None:
    """A boolean would not be a structural-risk report (FR-12)."""
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    failing = CheckResult(
        name="SLOT_COVERAGE",
        passed=False,
        resource="Lab_Info",
        missing_quantity=14.0,
        detail="short by 14 two-period windows",
    )
    run_store.save(dataclasses.replace(record.to(RunState.PREANALYSIS), pre_analysis=(failing,)))

    read = run_store.get("r1")
    assert read is not None
    assert read.pre_analysis[0].resource == "Lab_Info"
    assert read.pre_analysis[0].missing_quantity == 14.0


def test_the_diagnosis_keeps_the_two_flags_that_disambiguate_it(
    run_store: RunStore,
) -> None:
    """⚠️ An empty code list means two different things, and only
    `is_conclusive` separates them. Losing that flag in storage would turn
    "could not prove it" into "nothing wrong"."""
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    diagnosis = DiagnosisResult(
        conflicting_codes=(), is_minimal=False, is_conclusive=False, detail="inconclusive"
    )
    advanced = record.to(RunState.PREANALYSIS).to(RunState.SOLVING).to(RunState.INFEASIBLE)
    run_store.save(dataclasses.replace(advanced.to(RunState.DIAGNOSING), diagnosis=diagnosis))

    read = run_store.get("r1")
    assert read is not None
    assert read.diagnosis is not None
    assert read.diagnosis.conflicting_codes == ()
    assert read.diagnosis.is_conclusive is False
    assert read.diagnosis.is_minimal is False


def test_candidates_come_back_in_the_rank_order_they_were_written(
    run_store: RunStore,
) -> None:
    """⚠️ The order IS data. `domain.ts` says "display this order, do not sort",
    so a store that returned them in insertion or primary-key order would show
    a ranking nobody chose. Written deliberately worst-score-first so that a
    store which happened to sort by score would fail this."""
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    ordered = (candidate("c-low", 10.0), candidate("c-high", 90.0, slot=1))
    run_store.save(
        dataclasses.replace(
            record.to(RunState.PREANALYSIS).to(RunState.SOLVING).to(RunState.SCORING),
            candidates=ordered,
        )
    )

    read = run_store.get("r1")
    assert read is not None
    assert [c.id for c in read.candidates] == ["c-low", "c-high"]


def test_a_candidate_keeps_its_placements_and_sub_scores(run_store: RunStore) -> None:
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    run_store.save(
        dataclasses.replace(
            record.to(RunState.PREANALYSIS).to(RunState.SOLVING).to(RunState.SCORING),
            candidates=(candidate("c1", 80.0),),
        )
    )

    read = run_store.get("r1")
    assert read is not None
    only = read.candidates[0]
    assert only.placements == (Placement(session="s1", slot=0, room="R1"),)
    assert only.sub_scores == (SubScore(criterion="S2", raw_value=3.0, normalised=0.75),)
    assert only.cost == 7
    assert only.profile_name == "balanced"


def test_a_recorded_candidate_is_never_rewritten(run_store: RunStore) -> None:
    """⚠️ Invariant 6, enforced by the store having no update path.

    A candidate's sub-scores describe its content; editing it would leave them
    describing something that no longer exists. A regenerated timetable is a
    NEW candidate under a NEW run — so a later `save` carrying different
    candidates must not overwrite what was recorded.
    """
    import dataclasses

    record = new_run_record("r1", REQUEST, WEIGHTS)
    run_store.create(record)
    scoring = record.to(RunState.PREANALYSIS).to(RunState.SOLVING).to(RunState.SCORING)
    run_store.save(dataclasses.replace(scoring, candidates=(candidate("c1", 80.0),)))

    tampered = dataclasses.replace(scoring, candidates=(candidate("c1", 99.0, slot=27),))
    run_store.save(tampered)

    read = run_store.get("r1")
    assert read is not None
    assert read.candidates[0].score == 80.0
    assert read.candidates[0].placements[0].slot == 0


def test_runs_are_listed_newest_first(run_store: RunStore) -> None:
    import dataclasses

    first = new_run_record("r1", REQUEST, WEIGHTS)
    second = new_run_record("r2", REQUEST, WEIGHTS)
    first = dataclasses.replace(
        first, run=dataclasses.replace(first.run, created_at=datetime(2026, 8, 1, tzinfo=UTC))
    )
    second = dataclasses.replace(
        second, run=dataclasses.replace(second.run, created_at=datetime(2026, 8, 2, tzinfo=UTC))
    )
    run_store.create(first)
    run_store.create(second)

    assert [r.run.id for r in run_store.all()] == ["r2", "r1"]


# ── availability declarations ──────────────────────────────────────────


def test_a_teacher_who_never_declared_is_distinct_from_one_who_declared_nothing(
    availability_store,
) -> None:
    """⚠️ The distinction this whole store exists to keep.

    `None` means "not asked", so the instance's generated rows stand. `()`
    means "asked, and answered: I am free all week", which must WITHDRAW those
    generated rows. Collapsing the two would let a generated declaration pass
    for a real answer — which `docs/domain-model.md` requires must never happen.
    """
    assert availability_store.declarations("T001") is None

    availability_store.declare("T001", ())
    assert availability_store.declarations("T001") == ()
    assert "T001" in availability_store.declared_teachers()


def test_a_declaration_round_trips_with_its_state_and_source(availability_store) -> None:
    rows = build_declaration(
        "T001", semester=2, cells={5: AvailabilityState.UNAVAILABLE, 1: AvailabilityState.AVAILABLE}
    )
    availability_store.declare("T001", rows)

    read = availability_store.declarations("T001")
    assert read is not None
    # AVAILABLE cells are not stored - the instance records unavailability.
    assert [r.slot for r in read] == [5]
    assert read[0].state is AvailabilityState.UNAVAILABLE
    assert read[0].source is DeclarationSource.TEACHER
    assert read[0].semester == 2


def test_declaring_again_replaces_wholesale(availability_store) -> None:
    """A slot left free must clear a row that said otherwise, or a declaration
    could never be withdrawn (services/availability.py)."""
    availability_store.declare(
        "T001", build_declaration("T001", 2, {3: AvailabilityState.UNAVAILABLE})
    )
    availability_store.declare(
        "T001", build_declaration("T001", 2, {9: AvailabilityState.UNAVAILABLE})
    )

    read = availability_store.declarations("T001")
    assert read is not None
    assert [r.slot for r in read] == [9]


def test_one_teachers_declaration_does_not_touch_another(availability_store) -> None:
    availability_store.declare(
        "T001", build_declaration("T001", 2, {3: AvailabilityState.UNAVAILABLE})
    )
    availability_store.declare(
        "T002", build_declaration("T002", 2, {4: AvailabilityState.UNAVAILABLE})
    )

    first = availability_store.declarations("T001")
    assert first is not None
    assert [r.slot for r in first] == [3]
    assert availability_store.declared_teachers() == frozenset({"T001", "T002"})


# ── publications ───────────────────────────────────────────────────────


@pytest.fixture
def candidates_exist(session_factory: sessionmaker[Session]) -> None:
    """A run carrying candidates `c1` and `c2`, so a publication can name one.

    ⚠️ Needed because the database enforces what the in-memory store cannot:
    `publications.candidate_id` is a foreign key, so an orphan publication is
    refused outright. That asymmetry is not a divergence to fix — it is the
    database doing something a dict has no way to do, and the tests below are
    written to the stricter contract so both implementations satisfy it.
    """
    import dataclasses

    from optiedt.db.repositories import SqlRunStore

    store = SqlRunStore(session_factory)
    record = new_run_record("r1", REQUEST, WEIGHTS)
    store.create(record)
    store.save(
        dataclasses.replace(
            record.to(RunState.PREANALYSIS).to(RunState.SOLVING).to(RunState.SCORING),
            candidates=(candidate("c1", 80.0), candidate("c2", 70.0, slot=1)),
        )
    )


def test_a_publication_round_trips_with_its_run_and_author(
    publication_store, candidates_exist
) -> None:
    """The trace's own half: a publication that lost its run could not be
    traced back to a seed at all."""
    publication_store.publish(new_publication("c1", "r1", "responsable"))

    read = publication_store.for_candidate("c1")
    assert read is not None
    assert read.candidate == "c1"
    assert read.run == "r1"
    assert read.user == "responsable"
    assert read.published_at.tzinfo is not None


def test_publishing_the_same_candidate_twice_keeps_one_record(
    publication_store, candidates_exist
) -> None:
    publication_store.publish(new_publication("c1", "r1", "responsable"))
    publication_store.publish(new_publication("c1", "r1", "quelqu-un-dautre"))

    assert len(publication_store.all()) == 1
    read = publication_store.for_candidate("c1")
    assert read is not None
    assert read.user == "quelqu-un-dautre", "the later publication wins"


def test_an_unpublished_candidate_is_none(publication_store) -> None:
    assert publication_store.for_candidate("never-published") is None
    assert publication_store.all() == ()


def test_publications_come_back_newest_first(publication_store, candidates_exist) -> None:
    import time

    publication_store.publish(new_publication("c1", "r1", "responsable"))
    time.sleep(0.01)  # the clock is the ordering key; ties would be arbitrary
    publication_store.publish(new_publication("c2", "r1", "responsable"))

    assert [p.candidate for p in publication_store.all()] == ["c2", "c1"]
