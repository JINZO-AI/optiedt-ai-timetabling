"""Read `.ctt` instances and `.sol` solutions, plus locate the archives.

The `.ctt` format is **whitespace-token-based, not line-based**. The bundled
`validator/main.cpp` parses it with a bare `operator>>` stream — every header is
`<label> <value>`, every section is a label token followed by exactly the number
of records the header announced, and nothing depends on where the newlines fall.
`comp01.ctt` proves the point: its ROOMS rows are tab-separated and its CURRICULA
rows carry trailing spaces. Reading it line by line works until an instance puts
a record on two lines, so this reader tokenises, exactly as the validator does.

The `.sol` format is four tokens per lecture: `<course> <room> <day> <timeslot>`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from optiedt.validation.itc2007.problem import (
    Assignment,
    Course,
    Curriculum,
    Itc2007Instance,
    Room,
    Solution,
)

REFERENCE_SUBPATH = Path("data/reference/itc2007-cct-master/itc2007-cct-master")
"""Where `check-reference-data.ps1` expects the archive. The directory is
doubled because the download is a GitHub zip of a repository, unpacked whole -
see data/reference/PROVENANCE.md, which insists this is a source repository
that bundles the instances, not the competition archive itself."""


def repository_root() -> Path:
    """The project root, found from this file rather than the cwd.

    ``backend/src/optiedt/validation/itc2007/reader.py`` — five parents reach
    ``backend/`` and the sixth the root. A test invoked from any directory must
    find the same archives.
    """
    return Path(__file__).resolve().parents[5]


def archive_root() -> Path:
    return repository_root() / REFERENCE_SUBPATH


def archives_present() -> bool:
    """False on a fresh clone: `data/reference/` is gitignored on purpose.

    Every caller must branch on this rather than let a FileNotFoundError
    escape - the reference data is not part of the repository and its absence
    is a normal state, not a fault.
    """
    return (archive_root() / "datasets" / "comp01.ctt").is_file()


def instance_path(name: str) -> Path:
    return archive_root() / "datasets" / f"{name}.ctt"


def competition_instance_names() -> tuple[str, ...]:
    """`comp01` .. `comp21`, in order. The 21 verified in PROVENANCE.md.

    Fixed rather than globbed: the datasets directory also holds `toy` and
    `toytoy`, which are examples and not part of the competition set, and a
    silent change in what "the 21 instances" means is exactly the kind of drift
    the instance-count tests exist to catch.
    """
    return tuple(f"comp{index:02d}" for index in range(1, 22))


def _tokens(path: Path) -> Iterator[str]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            yield from line.split()


def read_instance(path: Path | str) -> Itc2007Instance:
    """Parse one `.ctt` file.

    Raises ValueError naming the section if the file runs out of tokens early,
    rather than returning an instance that is quietly short of courses.
    """
    path = Path(path)
    stream = _tokens(path)

    def take(section: str) -> str:
        try:
            return next(stream)
        except StopIteration as exhausted:
            raise ValueError(f"{path.name}: file ends inside {section}") from exhausted

    def header(section: str) -> str:
        take(section)  # the label - 'Name:', 'Courses:', ... - is not checked
        return take(section)

    name = header("the header")
    course_count = int(header("the header"))
    room_count = int(header("the header"))
    days = int(header("the header"))
    periods_per_day = int(header("the header"))
    curriculum_count = int(header("the header"))
    unavailability_count = int(header("the header"))

    take("COURSES")  # the section label
    courses = tuple(
        Course(
            id=take("COURSES"),
            teacher=take("COURSES"),
            lectures=int(take("COURSES")),
            min_working_days=int(take("COURSES")),
            students=int(take("COURSES")),
        )
        for _ in range(course_count)
    )

    take("ROOMS")
    rooms = tuple(Room(id=take("ROOMS"), capacity=int(take("ROOMS"))) for _ in range(room_count))

    take("CURRICULA")
    curricula: list[Curriculum] = []
    for _ in range(curriculum_count):
        curriculum_id = take("CURRICULA")
        size = int(take("CURRICULA"))
        curricula.append(
            Curriculum(
                id=curriculum_id,
                members=tuple(take("CURRICULA") for _ in range(size)),
            )
        )

    take("UNAVAILABILITY_CONSTRAINTS")
    unavailable: set[tuple[str, int]] = set()
    for _ in range(unavailability_count):
        course_id = take("UNAVAILABILITY_CONSTRAINTS")
        day = int(take("UNAVAILABILITY_CONSTRAINTS"))
        timeslot = int(take("UNAVAILABILITY_CONSTRAINTS"))
        unavailable.add((course_id, day * periods_per_day + timeslot))

    return Itc2007Instance(
        name=name,
        days=days,
        periods_per_day=periods_per_day,
        courses=courses,
        rooms=rooms,
        curricula=tuple(curricula),
        unavailable=frozenset(unavailable),
    )


def read_solution(path: Path | str, instance: Itc2007Instance) -> Solution:
    """Parse a `.sol` file: `<course> <room> <day> <timeslot>` per lecture.

    ``instance`` supplies ``periods_per_day`` for the day/timeslot -> period
    conversion, and nothing else. Unknown course or room names are **kept**, not
    dropped: the bundled validator skips them with a warning, but a name this
    project does not recognise means the reader and the file disagree, and
    silently discarding the row would hide that behind a plausible cost.
    """
    path = Path(path)
    stream = _tokens(path)
    assignments: list[Assignment] = []
    while (course := next(stream, None)) is not None:
        room = next(stream, None)
        day = next(stream, None)
        timeslot = next(stream, None)
        if room is None or day is None or timeslot is None:
            raise ValueError(
                f"{path.name}: partial record after {len(assignments)} complete entries"
            )
        assignments.append(
            Assignment(
                course=course,
                room=room,
                period=int(day) * instance.periods_per_day + int(timeslot),
            )
        )
    return tuple(assignments)


def write_solution(path: Path | str, solution: Solution, instance: Itc2007Instance) -> None:
    """Write a `.sol` the bundled C++ validator can read, for cross-checking.

    Sorted, so the file is reproducible for a given solution - the harness
    claims determinism (ADR-011) and an unordered dump would undermine that on
    inspection even when the timetable itself was identical.
    """
    path = Path(path)
    lines = sorted(
        f"{a.course} {a.room} {instance.day_of(a.period)} {instance.timeslot_of(a.period)}"
        for a in solution
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
