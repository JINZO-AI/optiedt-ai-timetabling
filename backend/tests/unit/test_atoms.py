from __future__ import annotations

import pytest

from optiedt.problem.atoms import TooManyAtomsError, atoms_of_groups, build_atoms
from tests.snapshot_builder import SnapshotBuilder


def _conflicts(builder: SnapshotBuilder) -> dict[tuple[str, str], bool]:
    problem = builder.problem()
    atoms = atoms_of_groups(build_atoms(problem), len(problem.groups))
    codes = {g.index: g.code for g in problem.groups}
    return {(codes[a], codes[b]): bool(atoms[a] & atoms[b]) for a in codes for b in codes if a != b}


def test_lmd_hierarchy_conflicts() -> None:
    b = SnapshotBuilder()
    cohort = b.group("L2", 60)
    g1 = b.group("G1", 30, cohort, "tutorial")
    g2 = b.group("G2", 30, cohort, "tutorial")
    b.group("G1a", 15, g1, "lab")
    b.group("G1b", 15, g1, "lab")
    b.group("G2a", 15, g2, "lab")
    c = _conflicts(b)
    assert c[("L2", "G1a")] is True  # a cohort lecture occupies every subgroup
    assert c[("G1", "G1a")] is True
    assert c[("G1", "G2")] is False  # disjoint tutorial groups can run in parallel
    assert c[("G1a", "G1b")] is False
    assert c[("G1a", "G2a")] is False
    assert c[("G1a", "G2")] is False


def test_orthogonal_partitions_overlap() -> None:
    b = SnapshotBuilder()
    cohort = b.group("L3", 90)
    b.group("G1", 45, cohort, "tutorial")
    b.group("G2", 45, cohort, "tutorial")
    b.group("EN", 60, cohort, "language")
    b.group("FR", 30, cohort, "language")
    c = _conflicts(b)
    assert c[("G1", "EN")] is True  # some G1 students take English
    assert c[("G1", "G2")] is False
    assert c[("EN", "FR")] is False


def test_partial_partition_keeps_students_outside_every_option() -> None:
    b = SnapshotBuilder()
    cohort = b.group("M1", 40)
    b.group("ELEC-AI", 10, cohort, "elective")
    problem = b.problem()
    atoms = build_atoms(problem)
    # one atom for the elective, one for the 30 students who do not take it
    assert sorted(round(a.size) for a in atoms) == [10, 30]


def test_atom_sizes_follow_partition_shares() -> None:
    b = SnapshotBuilder()
    cohort = b.group("L3", 90)
    b.group("G1", 45, cohort, "tutorial")
    b.group("G2", 45, cohort, "tutorial")
    b.group("EN", 60, cohort, "language")
    b.group("FR", 30, cohort, "language")
    atoms = build_atoms(b.problem())
    assert len(atoms) == 4
    assert sorted(round(a.size) for a in atoms) == [15, 15, 30, 30]
    assert round(sum(a.size for a in atoms)) == 90


def test_explosion_is_reported() -> None:
    b = SnapshotBuilder()
    cohort = b.group("BIG", 1000)
    for partition in range(10):
        for option in range(2):
            b.group(f"P{partition}-{option}", 500, cohort, f"part{partition}")
    with pytest.raises(TooManyAtomsError, match="BIG"):
        build_atoms(b.problem())
