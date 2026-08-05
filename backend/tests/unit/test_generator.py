"""The instance generator — the PPM §10 deliverable, held to its contract.

`data/generator/generate_instance.py` is standalone: it imports nothing from
`backend/`, because the 13 CSVs *are* the contract between the generator and
the application and neither side may depend on the other. So this test runs it
as a **subprocess**, exactly as a person would, and checks its output the same
way — by running `data/verification/verify_instance.py` against it.

⚠️ **What is asserted is the documented FIGURES, not the committed rows.** The
generator does not reproduce `data/instance/` byte for byte and does not claim
to: those files carry 425 student names and one particular teacher-to-session
assignment drawn from a random stream that was never committed. ADR-008's
binding is that *the documents state the instance's content and its five
verification results as facts*, and it is those that must survive — which is
what the assertions below cover.

⚠️ **`verify_instance.py` passing is necessary and not sufficient**, and C-13
is the reason that sentence is here rather than assumed. An instance can pass
every arithmetic check and still have no solution. The generated instance was
solved before this test was written — 218 of 218 sessions placed in 5.1 s — and
that measurement is recorded in `docs/status.md`. It is not repeated here
because it needs the solver and this suite must stay fast.
"""

from __future__ import annotations

import collections
import csv
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
GENERATOR = REPO / "data" / "generator" / "generate_instance.py"
VERIFIER = REPO / "data" / "verification" / "verify_instance.py"
COMMITTED = REPO / "data" / "instance"

FILES = [
    "programmes.csv",
    "promotions.csv",
    "groups.csv",
    "courses.csv",
    "sessions.csv",
    "teachers.csv",
    "rooms.csv",
    "slots.csv",
    "students.csv",
    "teacher_availability.csv",
    "holidays.csv",
    "calendar_config.csv",
    "constraint_catalogue.csv",
]


def _load(directory: pathlib.Path, name: str) -> list[dict[str, str]]:
    with open(directory / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("generated-instance")
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return out


def test_it_writes_all_thirteen_files(generated: pathlib.Path) -> None:
    """Thirteen, and only thirteen. The contract is the whole set."""
    written = sorted(p.name for p in generated.glob("*.csv"))

    assert written == sorted(FILES)


def test_the_output_passes_the_documentation_check(generated: pathlib.Path) -> None:
    """⚠️ **The assertion that actually matters.**

    `verify_instance.py` is the contract between the generator and the
    application, and it does not know or care which of the two produced the
    files it reads. If the generator ever drifts from the documented figures,
    this fails with the same message a person would see.
    """
    result = subprocess.run(
        [sys.executable, str(VERIFIER), "--instance", str(generated)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All checks passed" in result.stdout


def test_it_is_deterministic(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Two runs, byte-identical output.

    A generator whose output moved between runs could not be a deliverable: the
    figures it is held to would depend on when it was invoked. There is no
    seeded RNG here at all - names come from fixed pools by index - because
    `random`'s stream is not stable across Python versions, and a deliverable
    whose output changes with the interpreter is not one.
    """
    first = tmp_path_factory.mktemp("gen-a")
    second = tmp_path_factory.mktemp("gen-b")
    for out in (first, second):
        assert (
            subprocess.run(
                [sys.executable, str(GENERATOR), "--out", str(out)], check=False
            ).returncode
            == 0
        )

    for name in FILES:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_it_refuses_to_overwrite_the_committed_instance() -> None:
    """⚠️ Because overwriting it would invalidate every measurement in `docs/`
    without a single one failing.

    Scores, timings, the S5 range, the occupancy figures on the timetable
    screen - all were taken against the committed rows, and the generator
    reproduces the FIGURES rather than the rows. A generator that silently
    replaced them would leave the documentation self-consistent and wrong.
    """
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--out", str(COMMITTED)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Refusing to overwrite" in result.stderr


@pytest.mark.parametrize(
    ("name", "column"),
    [
        ("sessions.csv", "session_type"),
        ("sessions.csv", "duration_periods"),
        ("sessions.csv", "required_room_type"),
        ("groups.csv", "group_type"),
        ("rooms.csv", "room_type"),
        ("teachers.csv", "rank"),
        ("courses.csv", "credits"),
        ("holidays.csv", "is_islamic"),
    ],
)
def test_the_aggregate_profile_matches_the_committed_instance(
    generated: pathlib.Path, name: str, column: str
) -> None:
    """The distributions the documentation states, column by column.

    Not row equality - see the module docstring - but every count a document
    quotes. 32/82/104 sessions, 114/104 durations, 6/15/30 groups, 2/7/8/3
    rooms, 7/11/13/13 ranks, 14/8/10 credits, 18 holidays of which 10 lunar.
    """
    assert collections.Counter(r[column] for r in _load(generated, name)) == collections.Counter(
        r[column] for r in _load(COMMITTED, name)
    )


@pytest.mark.parametrize("name", FILES)
def test_every_file_has_the_committed_schema(generated: pathlib.Path, name: str) -> None:
    """Same columns, same order.

    The loader reads by column name, so a reordering would not break it - but
    the 13 files are a published contract, and a generator emitting a different
    shape of the same data has not reproduced it.
    """
    generated_rows = _load(generated, name)
    committed_rows = _load(COMMITTED, name)

    assert list(generated_rows[0]) == list(committed_rows[0])
    assert len(generated_rows) == len(committed_rows)


def test_every_declaration_is_marked_synthetic(generated: pathlib.Path) -> None:
    """ADR-008's honesty marker, and it is not decoration.

    A generated declaration and a real one must be distinguishable at any
    moment, because S5 carries weight 0.20 while measuring a labelled proxy
    rather than anything a teacher said (C-12).
    """
    rows = _load(generated, "teacher_availability.csv")

    assert {r["source"] for r in rows} == {"SYNTHETIC"}
    assert {r["is_available"] for r in rows} == {"0"}
